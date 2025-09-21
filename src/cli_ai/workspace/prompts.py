"""
Workspace-aware prompts that integrate task memory for smarter decision making.

These prompts provide context about previous actions, learned knowledge,
and task progress to prevent redundant operations and improve efficiency.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .core import TaskWorkspace
from ..tools.tools import tools_schema, get_tool_docstrings


def get_workspace_aware_need_assessment_prompt(
    history: list, 
    current_working_directory: str, 
    recalled_memories: list, 
    voice_input_enabled: bool,
    workspace: Optional[TaskWorkspace] = None
) -> str:
    """
    Enhanced Phase 1 prompt that includes workspace context to prevent redundant actions.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    persona = "You are voice enabled." if voice_input_enabled else "You are text-based."
    
    memory_context = ""
    if recalled_memories:
        memory_context = "\n**Recalled Memories:**\n"
        for memory in recalled_memories:
            memory_context += f"- {memory}\n"

    # Add workspace context to prevent redundant actions
    workspace_context = ""
    redundancy_check = ""
    if workspace:
        workspace_context = f"""
**Task Workspace Context:**
Task: {workspace.original_request}
Current Goal: {workspace.current_goal}
Actions Taken: {len(workspace.actions_taken)}
Status: {workspace.progress_state}

Accumulated Knowledge:
"""
        for key, value in workspace.accumulated_knowledge.items():
            workspace_context += f"  {key}: {value}\n"

        # Recent actions summary
        if workspace.actions_taken:
            workspace_context += "\nRecent Actions:\n"
            for action in workspace.actions_taken[-3:]:  # Last 3 actions
                workspace_context += f"  - {action.tool}({action.args}) -> {action.thought}\n"

        redundancy_check = """
**CRITICAL - AVOID REDUNDANCY:**
- If the workspace shows you've already done a similar action, don't repeat it
- Use accumulated knowledge instead of re-gathering the same information
- Build on previous actions rather than starting over
"""

    return f"""You are an expert autonomous agent that analyzes user requests to determine if tools are needed.

{persona}

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memory_context}
{workspace_context}
{redundancy_check}

**Previous Conversation:**
{history_str}

Your task is to determine if the current user request requires tools to complete, or if it can be answered directly with a text response.

**Analysis Framework:**
1. **Check Workspace First**: Review any previous actions and accumulated knowledge
2. **Information Needs**: What information is required to answer the user?
3. **Tool Requirements**: Do you need to gather data, perform actions, or can you respond directly?
4. **Redundancy Check**: Has this information already been gathered in the workspace?

**Response Format (JSON only):**

For requests that can be answered directly:
{json.dumps({"needs_tools": False, "reasoning": "The workspace already contains a list of files from previous list_directory action", "response": "Based on the directory listing I performed earlier, the assets/images folder contains 15 image files including cats, dogs, and landscapes."})}

For simple questions or greetings:
{json.dumps({"needs_tools": False, "reasoning": "This is a greeting that requires no system interaction", "response": "Hello! How can I help you today?"})}

For requests requiring tools:
{json.dumps({"needs_tools": True, "reasoning": "User wants to analyze image content, which requires the describe_image tool", "response": ""})}

Analyze the request considering workspace context and respond with appropriate JSON.
"""


def get_workspace_aware_tool_selection_prompt(
    history: list, 
    current_working_directory: str, 
    original_user_request: str, 
    voice_input_enabled: bool,
    workspace: Optional[TaskWorkspace] = None
) -> str:
    """
    Enhanced Phase 2 prompt that includes workspace context for intelligent tool selection.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    persona = "You are voice enabled." if voice_input_enabled else "You are text-based."

    # Add workspace context
    workspace_context = ""
    redundancy_check = ""
    if workspace:
        workspace_context = f"""
**Current Task Workspace:**
Task: {workspace.original_request}
Current Goal: {workspace.current_goal}

**Action History:**
{workspace.get_action_history_summary()}

**CRITICAL - AVOID REDUNDANCY:**
- Check the action history above before selecting a tool
- If you've already gathered information, use it instead of re-gathering
- Build on previous work rather than repeating actions
- Only list directories if you haven't done so recently for the same path
"""

    return f"""You are an expert autonomous agent that executes tasks using available tools with workspace awareness.

{persona}

**Current Working Directory:** {current_working_directory}
{workspace_context}

**AVAILABLE TOOLS:**
{json.dumps(tools_schema, indent=2)}

**Previous Conversation:**
{history_str}

The user request requires tools to complete. Analyze the available tools and workspace context to determine:
1. Can you complete this task with the available tools?
2. What is the logical first/next action based on workspace history?
3. Are you avoiding redundant actions?

If you CAN complete the task, respond with:
{{
    "can_complete": true,
    "action": {{
        "thought": "What you're thinking and why this action makes sense given workspace context",
        "current_goal": "The specific goal for this step",
        "tool": "tool_name_here",
        "args": {{"parameter1": "value1", "parameter2": "value2"}},
        "is_critical": true/false,
        "original_user_request": "{original_user_request}"
    }}
}}

If you CANNOT complete the task, respond with:
{{
    "can_complete": false,
    "reasoning": "Explanation of why the task cannot be completed with available tools",
    "suggestion": "Alternative approach or request for clarification"
}}

**Critical Instructions:**
- ONLY use tools from the available tools list above
- Use EXACT parameter names as shown in the tools schema
- Consider workspace context to avoid repeating successful actions
- Build logically on previous actions and knowledge

Respond with JSON only.
"""


def get_workspace_reflexion_prompt(
    history: list,
    current_goal: str,
    original_user_request: str,
    voice_input_enabled: bool,
    workspace: Optional[TaskWorkspace] = None,
    relevant_memories: list = None
) -> str:
    """
    Enhanced reflexion prompt with workspace awareness and tools schema.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    persona = "You are voice enabled." if voice_input_enabled else "You are text-based."
    
    memory_context = ""
    if relevant_memories:
        memory_context = "\n**Relevant Past Experiences:**\n"
        for i, memory in enumerate(relevant_memories[:3], 1):
            memory_context += f"{i}. {memory}\n"
        memory_context += "\nUse these past experiences to inform your decision-making and avoid repeating mistakes.\n"

    # Add workspace context
    workspace_context = ""
    progress_analysis = ""
    if workspace:
        workspace_context = f"""
**Task Workspace:**
{workspace.get_progress_summary()}

**Action History:**
{workspace.get_action_history_summary()}
"""
        progress_analysis = """
**WORKSPACE-AWARE ANALYSIS:**
- Consider the overall progress toward the original goal
- Evaluate if the last action moved you closer to completion
- Plan the next logical step based on accumulated knowledge
- Avoid repeating actions that have already been successful
"""

    return f"""You are a ReAct-style agent. You have just performed an action and observed the result.

{persona}

**Current Goal:**
{current_goal}

**Original User Request:**
{original_user_request}
{memory_context}
{workspace_context}

**AVAILABLE TOOLS:**
{json.dumps(tools_schema, indent=2)}

**Conversation History:**
{history_str}
{progress_analysis}

Your task is to analyze the observation and workspace context to decide whether the user request has been fulfilled or if further action is needed.

**WORKSPACE-AWARE DECISION MAKING:**
- Review the workspace to understand overall progress
- Consider what information you've already gathered
- Determine if you have enough to complete the original request
- Plan logical next steps that build on previous work
- ONLY use tools from the available tools list above with correct parameters

You have three choices for the 'decision' key in your JSON response:

1.  **"continue"**: If the task is not yet complete and you need to perform another action.
    *   **"comment"**: Brief explanation of why you're continuing and what you plan to do next
    *   **"next_action"**: A dictionary containing the next tool to use and the arguments:
        *   **"thought"**: What you're trying to accomplish with this action
        *   **"current_goal"**: The UPDATED current goal for this next step
        *   **"tool"**: The tool name to use (MUST be from available tools above)
        *   **"args"**: The arguments for the tool (MUST match tool schema)
        *   **"is_critical"**: Risk assessment (true for write_file, destructive commands; false for read operations)
        *   **"workspace_reasoning"**: How this action builds on workspace knowledge

2.  **"finish"**: If the task is complete and you have the final answer for the user.
    *   **"comment"**: The final answer for the user, incorporating all workspace knowledge

3.  **"error"**: If the last action resulted in an error that you cannot recover from.
    *   **"comment"**: A brief explanation of the error

**Example Continue with Workspace Awareness:**
{json.dumps({
    "decision": "continue",
    "comment": "I have the file list from the previous action. Now I need to analyze the first image to determine sorting categories.",
    "next_action": {
        "thought": "Analyze the first image to identify its content for creating sorting categories",
        "current_goal": "Determine image content categories for sorting the assets/images files",
        "tool": "describe_image",
        "args": {"image_path": "assets/images/first_image.jpg", "question": "What animal or object is shown in this image?"},
        "is_critical": False,
        "workspace_reasoning": "Building on the file list obtained earlier, now categorizing images by content"
    }
})}

**Example Finish:**
{json.dumps({
    "decision": "finish",
    "comment": "I have successfully analyzed all images and sorted them into categories: Animals (deer, giraffe, fox), Landscapes (3 files), and Objects (2 files). The images are now organized by their primary content."
})}

Now, analyze the conversation history and workspace context and generate the appropriate JSON response.
"""
