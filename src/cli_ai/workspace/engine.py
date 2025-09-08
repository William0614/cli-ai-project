"""
Workspace-aware AI engine that integrates TaskWorkspace with the two-phase thinking process.

This module provides enhanced agent intelligence by maintaining persistent task memory
and making decisions based on accumulated knowledge and previous actions.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..core.ai_engine import get_client, print_prompt_debug, get_latest_user_input
from ..utils.os_helpers import get_os_info
from .prompts import (
    get_workspace_aware_need_assessment_prompt,
    get_workspace_aware_tool_selection_prompt,
    get_workspace_reflexion_prompt
)
from .core import TaskWorkspace, WorkspaceManager


class WorkspaceAwareEngine:
    """
    Enhanced AI engine that uses TaskWorkspace for persistent task memory.
    """
    
    def __init__(self, workspace_manager: WorkspaceManager = None):
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.current_workspace: Optional[TaskWorkspace] = None
    
    async def think_with_workspace(
        self, 
        history: list, 
        current_working_directory: str, 
        voice_input_enabled: bool, 
        user_info_manager=None, 
        vector_memory_manager=None,
        task_id: Optional[str] = None
    ) -> Tuple[dict, Optional[str]]:
        """
        Enhanced two-phase thinking with workspace awareness.
        
        Returns:
            (response_dict, task_id): The agent's response and the task ID for tracking
        """
        latest_user_message = get_latest_user_input(history)
        
        # Determine if this is a new task or continuation
        if task_id:
            workspace = self.workspace_manager.get_workspace(task_id)
        else:
            # Create new workspace for new task
            workspace = self.workspace_manager.create_workspace(latest_user_message)
            task_id = workspace.task_id
        
        self.current_workspace = workspace
        
        # Get relevant memories (same as before)
        recalled_memories = []
        
        if vector_memory_manager and latest_user_message:
            try:
                relevant_contexts = vector_memory_manager.search_relevant_context(
                    query=latest_user_message,
                    limit=3,
                    min_similarity=0.5
                )
                for context in relevant_contexts:
                    recalled_memories.append({
                        'content': context.get('content', ''),
                        'timestamp': context.get('timestamp', 'retrieved_memory')
                    })
            except Exception as e:
                print(f"[Vector Memory] Error retrieving context: {e}")
        
        if user_info_manager:
            user_info_data = user_info_manager.get_user_info()
            if user_info_data:
                for info in user_info_data[:10]:
                    recalled_memories.append({
                        'content': f"User {info['category']}: {info['key']} = {info['value']}",
                        'timestamp': info.get('timestamp', 'user_info')
                    })

        # PHASE 1: Workspace-aware need assessment
        phase1_prompt = (
            "You are a cli-assistant that analyzes user requests with task memory.\n" + 
            get_os_info() + "\n" + 
            get_workspace_aware_need_assessment_prompt(
                history, current_working_directory, recalled_memories, voice_input_enabled, workspace
            )
        )

        print_prompt_debug(phase1_prompt, latest_user_message, "WORKSPACE PHASE 1: NEED ASSESSMENT")

        try:
            phase1_response = await get_client().chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": phase1_prompt},
                    {"role": "user", "content": latest_user_message}
                ],
                response_format={"type": "json_object"}
            )
            
            phase1_result = json.loads(phase1_response.choices[0].message.content)
            
            # Log the decision in workspace
            workspace.update_knowledge("phase1_decision", phase1_result)
            
            # If no tools needed, return direct response
            if not phase1_result.get("needs_tools", False):
                workspace.progress_state = "completed"
                self.workspace_manager.update_workspace(workspace)
                return {"text": phase1_result.get("response", "I understand, but I don't have a specific response.")}, task_id
            
            # PHASE 2: Workspace-aware tool selection
            phase2_prompt = (
                "You are a cli-assistant that executes tasks with workspace awareness.\n" + 
                get_os_info() + "\n" + 
                get_workspace_aware_tool_selection_prompt(
                    history, current_working_directory, latest_user_message, voice_input_enabled, workspace
                )
            )

            print_prompt_debug(phase2_prompt, latest_user_message, "WORKSPACE PHASE 2: TOOL SELECTION")

            phase2_response = await get_client().chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": phase2_prompt},
                    {"role": "user", "content": latest_user_message}
                ],
                response_format={"type": "json_object"}
            )
            
            phase2_result = json.loads(phase2_response.choices[0].message.content)
            
            # If tools can't complete the task, return explanation
            if not phase2_result.get("can_complete", False):
                workspace.progress_state = "failed"
                self.workspace_manager.update_workspace(workspace)
                return {
                    "text": f"I cannot complete this task with the available tools. {phase2_result.get('reasoning', '')} {phase2_result.get('suggestion', '')}"
                }, task_id
            
            # Record the intended action in workspace before execution
            action = phase2_result["action"]
            action_id = workspace.add_action(
                tool=action["tool"],
                args=action["args"],
                thought=action["thought"],
                goal=action["current_goal"]
            )
            
            # Update workspace state
            workspace.progress_state = "executing"
            self.workspace_manager.update_workspace(workspace)
            
            # Return the action with workspace metadata
            response = {
                "action": action,
                "original_user_request": phase2_result.get("original_user_request", latest_user_message),
                "_workspace_action_id": action_id  # Internal tracking
            }
            
            return response, task_id

        except Exception as e:
            print(f"Error in workspace-aware thinking: {e}")
            workspace.progress_state = "error"
            workspace.update_knowledge("error", str(e))
            self.workspace_manager.update_workspace(workspace)
            return {"text": "Sorry, an error occurred while processing your request."}, task_id
    
    def record_action_result(self, task_id: str, action_id: str, status: str, output: Any, extracted_info: Dict[str, Any] = None):
        """
        Record the result of an action execution in the workspace.
        """
        workspace = self.workspace_manager.get_workspace(task_id)
        if workspace:
            workspace.add_observation(action_id, status, output, extracted_info or {})
            
            # Extract useful information from the output for future reference
            if status == "Success" and output:
                self._extract_knowledge_from_output(workspace, output)
            
            workspace.progress_state = "waiting_for_next_step"
            self.workspace_manager.update_workspace(workspace)
    
    def _extract_knowledge_from_output(self, workspace: TaskWorkspace, output: Any):
        """
        Extract useful knowledge from action outputs and store in workspace.
        """
        if isinstance(output, dict):
            # Extract file lists from directory listings
            if "result" in output and isinstance(output["result"], list):
                # Looks like a file/directory listing
                workspace.update_knowledge("last_directory_listing", output["result"])
            
            # Extract image analysis results
            if "response" in output and "image_path" in output:
                image_analyses = workspace.get_knowledge("image_analyses", {})
                image_analyses[output["image_path"]] = output["response"]
                workspace.update_knowledge("image_analyses", image_analyses)
    
    async def reflexion_with_workspace(
        self, 
        history: list, 
        current_goal: str, 
        original_user_request: str, 
        voice_input_enabled: bool,
        task_id: str,
        vector_memory_manager=None
    ) -> dict:
        """
        Enhanced reflexion with workspace context.
        """
        workspace = self.workspace_manager.get_workspace(task_id)
        if not workspace:
            return {"decision": "error", "comment": "Workspace not found for task."}
        
        # Get relevant memories from vector database if available
        relevant_memories = []
        if vector_memory_manager:
            try:
                search_query = f"{current_goal} {original_user_request}"
                if history:
                    recent_actions = " ".join([str(msg.get('content', ''))[:100] for msg in history[-3:]])
                    search_query += f" {recent_actions}"
                
                relevant_memories = vector_memory_manager.search_relevant_context(search_query, limit=5)
            except Exception as e:
                print(f"Warning: Could not retrieve relevant memories for reflexion: {e}")
        
        latest_user_message = get_latest_user_input(history)
        
        # Use workspace-aware reflexion prompt
        system_prompt = get_workspace_reflexion_prompt(
            history, current_goal, original_user_request, voice_input_enabled, workspace, relevant_memories
        )

        print_prompt_debug(system_prompt, latest_user_message, "WORKSPACE REFLEXION")

        try:
            response = await get_client().chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": latest_user_message}
                ],
                max_completion_tokens=2000,
                response_format={"type": "json_object"}
            )

            raw_response_content = response.choices[0].message.content
            if not raw_response_content.strip():
                print("LLM returned an empty response for reflexion.")
                return {"decision": "error", "comment": "LLM returned an empty response during reflection."}
            
            decision = json.loads(raw_response_content)
            
            # Update workspace based on decision
            if decision.get("decision") == "finish":
                workspace.progress_state = "completed"
                self.workspace_manager.close_workspace(task_id)
            elif decision.get("decision") == "continue":
                workspace.progress_state = "planning_next_action"
                # Record the planned next action
                if "next_action" in decision:
                    next_action = decision["next_action"]
                    action_id = workspace.add_action(
                        tool=next_action["tool"],
                        args=next_action["args"],
                        thought=next_action["thought"],
                        goal=next_action["current_goal"]
                    )
                    decision["next_action"]["_workspace_action_id"] = action_id
            else:
                workspace.progress_state = "error"
            
            self.workspace_manager.update_workspace(workspace)
            return decision

        except Exception as e:
            print(f"An error occurred during workspace reflexion: {e}")
            workspace.progress_state = "error"
            workspace.update_knowledge("reflexion_error", str(e))
            self.workspace_manager.update_workspace(workspace)
            return {"decision": "error", "comment": "Sorry, an error occurred during reflection."}
    
    def get_workspace_summary(self, task_id: str) -> Optional[str]:
        """Get a summary of the current workspace state."""
        workspace = self.workspace_manager.get_workspace(task_id)
        if workspace:
            return workspace.get_progress_summary()
        return None
    
    def cleanup_completed_workspaces(self, max_age_hours: int = 24):
        """Clean up old completed workspaces."""
        self.workspace_manager.cleanup_old_workspaces(max_age_hours)
