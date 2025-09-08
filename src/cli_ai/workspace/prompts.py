"""
Workspace-aware prompts that integrate task memory for smarter decision making.

These prompts provide context about previous actions, learned knowledge,
and task progress to prevent redundant operations and improve efficiency.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .core import TaskWorkspace


def get_workspace_aware_need_assessment_prompt(
    history: list, 
    current_working_directory: str, 
    recalled_memories: List[Dict[str, Any]], 
    voice_input_enabled: bool,
    workspace: Optional[TaskWorkspace] = None
) -> str:
    """
    Enhanced Phase 1 prompt that includes workspace context for smarter need assessment.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    memories_str = ""
    if recalled_memories:
        memories_list = [f"- {m['content']} (timestamp: {m['timestamp']})" for m in recalled_memories]
        memories_str = "\n".join(memories_list)
    
    persona = "You are voice enabled. You interact with the user by speaking aloud." if voice_input_enabled else "You interact with the user through command line text interface."

    # Add workspace context
    workspace_context = ""
    if workspace:
        workspace_context = f"""
**Task Workspace Context:**
{workspace.get_progress_summary()}

**Previous Actions & Results:**
{workspace.get_action_history_summary()}

**IMPORTANT: Review the workspace context above before deciding on actions. If you already have the information you need from previous actions, don't repeat them!**
"""

    return f"""You are an expert autonomous agent that analyzes user requests to determine if tools are needed.

{persona}

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memories_str}
{workspace_context}
**Conversation History:**
{history_str}

**Your Task:**
Analyze the user's latest request and determine if it needs tools to complete or can be answered directly with text.

**WORKSPACE-AWARE GUIDELINES:**
- **Check workspace first**: If the workspace contains relevant information from previous actions, use it instead of repeating actions
- **Direct Response**: Simple questions, greetings, explanations that don't require tools OR when workspace already contains the needed information
- **Needs Tools**: File operations, shell commands, image analysis, directory listings ONLY if not already done or if new information is needed

**Response Format:**
Return a JSON object with these exact keys:

{{
    "needs_tools": boolean,
    "reasoning": "Brief explanation of your decision, mentioning workspace context if relevant",
    "response": "If needs_tools is false, provide the direct response here. If true, leave empty."
}}

**Examples:**

Direct response using workspace knowledge:
{json.dumps({"needs_tools": False, "reasoning": "The workspace already contains a list of files from previous list_directory action", "response": "Based on the directory listing I performed earlier, the assets/images folder contains 14 image files including various animal photos."})}

Direct response (simple question):
{json.dumps({"needs_tools": False, "reasoning": "This is a greeting that requires no system interaction", "response": "Hello! How can I help you today?"})}

Needs tools (new action required):
{json.dumps({"needs_tools": True, "reasoning": "User wants to analyze image content, which requires the describe_image tool", "response": ""})}

Analyze the user's request now and respond with the JSON format above.
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
{workspace.get_progress_summary()}

**Action History:**
{workspace.get_action_history_summary()}
"""
        redundancy_check = """
**CRITICAL - AVOID REDUNDANCY:**
- Check the action history above before selecting a tool
- If you've already performed the same action with the same parameters, DON'T repeat it
- Use the results from previous actions that are available in the workspace
- Only perform new actions if you need additional or different information
"""

    # Import tools schema
    from ..tools.tools import tools_schema

    return f"""You are an expert autonomous agent that executes tasks using available tools.

{persona}

**Current Working Directory:** {current_working_directory}

**Original User Request:** {original_user_request}
{workspace_context}
**Conversation History:**
{history_str}
{redundancy_check}
**Available Tools:**
{json.dumps(tools_schema, indent=2)}

**Your Task:**
The user request requires tools to complete. Analyze the available tools and workspace context to determine:
1. Can you complete this task with the available tools?
2. What is the next action to take (considering what's already been done)?

**WORKSPACE-AWARE TOOL SELECTION:**
- Review action history to avoid repeating identical operations
- Build upon previous results stored in the workspace
- Select tools that advance the task toward completion
- Consider the overall goal, not just the immediate step

**Response Format:**
Return a JSON object with one of these structures:

**If you CAN complete the task:**
{{
    "can_complete": true,
    "original_user_request": "{original_user_request}",
    "action": {{
        "thought": "Brief description considering workspace context and avoiding redundancy",
        "current_goal": "Specific goal this action aims to achieve",
        "tool": "exact_tool_name_from_schema",
        "args": {{"exact_parameter_name": "value"}},
        "is_critical": true/false,
        "workspace_reasoning": "Why this action is needed given the workspace context"
    }}
}}

**If you CANNOT complete the task:**
{{
    "can_complete": false,
    "reasoning": "Explanation of why the task cannot be completed with available tools",
    "suggestion": "Alternative suggestion for the user"
}}

**Critical Instructions for is_critical field:**
- write_file: always true
- run_shell_command: true for destructive operations (rm, sudo, mv, delete, format, kill), false for safe operations (ls, pwd, echo, git status)
- All other tools (read_text_file, list_directory, describe_image, find_similar_images): always false

Generate your response now.
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
    Enhanced reflexion prompt that considers workspace context for better planning.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    persona = "You are voice enabled." if voice_input_enabled else "You are text-based."
    
    # Include relevant memories if available
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
**Conversation History:**
{history_str}
{progress_analysis}

Your task is to analyze the observation and workspace context to decide whether the user request has been fulfilled or if further action is needed.

**WORKSPACE-AWARE DECISION MAKING:**
- Review the workspace to understand overall progress
- Consider what information you've already gathered
- Determine if you have enough to complete the original request
- Plan logical next steps that build on previous work

You have three choices for the 'decision' key in your JSON response:

1.  **"continue"**: If the task is not yet complete and you need to perform another action.
    *   **"comment"**: Brief explanation of why you're continuing and what you plan to do next
    *   **"next_action"**: A dictionary containing the next tool to use and the arguments:
        *   **"thought"**: What you're trying to accomplish with this action
        *   **"current_goal"**: The UPDATED current goal for this next step
        *   **"tool"**: The tool name to use
        *   **"args"**: The arguments for the tool
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
