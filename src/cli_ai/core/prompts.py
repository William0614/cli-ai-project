import json
from typing import List, Dict, Any
from ..tools.tools import tools_schema, get_tool_docstrings

def get_need_assessment_prompt(history: list, current_working_directory: str, recalled_memories: List[Dict[str, Any]], voice_input_enabled: bool) -> str:
    """
    Phase 1: Determine if the user request needs tools or can be answered directly.
    This reduces tool hallucinations by separating need assessment from tool selection.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    memories_str = ""
    if recalled_memories:
        memories_list = [f"- {m['content']} (timestamp: {m['timestamp']})" for m in recalled_memories]
        memories_str = "\n".join(memories_list)
    
    persona = "You are voice enabled. You interact with the user by speaking aloud." if voice_input_enabled else "You interact with the user through command line text interface."

    return f"""You are an expert autonomous agent that analyzes user requests to determine if tools are needed.

{persona}

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memories_str}

**Conversation History:**
{history_str}

**Your Task:**
Analyze the user's latest request and determine if it needs tools to complete or can be answered directly with text.

**Guidelines for Direct Response (no tools needed):**
- Simple questions, greetings, explanations
- General knowledge queries
- Conversations that don't require system interaction
- Clarifications or confirmations

**Guidelines for Tool Usage (tools needed):**
- File operations (read, write, list)
- Shell commands or system tasks
- Image analysis or processing
- Directory operations
- Any task requiring system interaction

**Response Format:**
Return a JSON object with these exact keys:

{{
    "needs_tools": boolean,
    "reasoning": "Brief explanation of your decision",
    "response": "If needs_tools is false, provide the direct response here. If true, leave empty."
}}

**Examples:**

Direct response (no tools):
{json.dumps({"needs_tools": False, "reasoning": "This is a greeting that requires no system interaction", "response": "Hello! How can I help you today?"})}

Needs tools:
{json.dumps({"needs_tools": True, "reasoning": "User wants to list files, which requires the list_directory tool", "response": ""})}

Analyze the user's request now and respond with the JSON format above.
"""

def get_tool_selection_prompt(history: list, current_working_directory: str, original_user_request: str, voice_input_enabled: bool) -> str:
    """
    Phase 2: Select appropriate tools to complete the task.
    Only called when Phase 1 determines tools are needed.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    persona = "You are voice enabled." if voice_input_enabled else "You are text-based."

    return f"""You are an expert autonomous agent that executes tasks using available tools.

{persona}

**Current Working Directory:** {current_working_directory}

**Original User Request:** {original_user_request}

**Conversation History:**
{history_str}

**Available Tools:**
{json.dumps(tools_schema, indent=2)}

**Your Task:**
The user request requires tools to complete. Analyze the available tools and determine:
1. Can you complete this task with the available tools?
2. What is the next action to take?

**CRITICAL: Use ONLY the tools listed above with their EXACT parameter names.**

**Response Format:**
Return a JSON object with one of these structures:

**If you CAN complete the task:**
{{
    "can_complete": true,
    "original_user_request": "{original_user_request}",
    "action": {{
        "thought": "Brief description of what you are trying to do",
        "current_goal": "Specific goal this action aims to achieve",
        "tool": "exact_tool_name_from_schema",
        "args": {{"exact_parameter_name": "value"}},
        "is_critical": true/false
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

def get_reflexion_prompt(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool, relevant_memories: list = None) -> str:
    """
    Generates a prompt for the LLM to reflect on the result of an action.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    if voice_input_enabled:
        persona = "You are voice enabled."
    else:
        persona = "You are text-based."
    
    # Include relevant memories if available
    memory_context = ""
    if relevant_memories:
        memory_context = "\n**Relevant Past Experiences:**\n"
        for i, memory in enumerate(relevant_memories[:3], 1):  # Limit to 3 most relevant
            memory_context += f"{i}. {memory}\n"
        memory_context += "\nUse these past experiences to inform your decision-making and avoid repeating mistakes.\n"

    return f"""You are a ReAct-style agent. You have just performed an action and observed the result.

{persona}

**Current Goal:**
{current_goal}

**Original User Request:**
{original_user_request}
{memory_context}
**Conversation History:**
{history_str}

Your task is to analyze the observation in conversation history and decide whether the user request has been fulfilled or if further action is needed.
If the observation is from a `run_shell_command`, you should parse the `stdout` to find the relevant information. 
If the original user request has been fully addressed and completed, you MUST return 'finish'. You have three choices for the 'decision' key in your JSON response:

1.  **"continue"**: If the task is not yet complete and you need to perform another action.
    *   **"comment"**: A brief explanation of why you are continuing and what you plan to do next.
    *   **"next_action"**: A dictionary containing the next tool to use and the arguments. **MUST include "is_critical" field:**
        *   **"thought"**: What you're trying to accomplish with this action.
        *   **"current_goal"**: The UPDATED current goal for this next step.
        *   **"tool"**: The tool name to use.
        *   **"args"**: The arguments for the tool.
        *   **"is_critical"**: Risk assessment:
            *   `write_file`: Always `true`.
            *   `run_shell_command`: `true` if the command modifies the system or data (e.g., `rm`, `sudo`, `mv`, `delete`, `format`, `kill`, `reboot`, `shutdown`, `apt remove`, `npm uninstall`, `pip uninstall`, `git commit`, `git push`). Otherwise, `false` (e.g., `ls`, `pwd`, `echo`, `git status`, `git log`).
            *   All other tools (`read_file`, `list_directory`, `describe_image`, `find_similar_images`): Always `false`.

**Make goals SPECIFIC and PROGRESSIVE:**

2.  **"finish"**: If the task is complete and you have the final answer for the user.
    *   **"comment"**: The final answer for the user.

3.  **"error"**: If the last action resulted in an error that you cannot recover from.
    *   **"comment"**: A brief explanation of the error.

**Example Continue:**
{json.dumps({
    "decision": "continue",
    "comment": "I have listed the files. Now I need to analyze the first image to understand what type of content it contains.",
    "next_action": {
        "thought": "Analyze the first image to identify its content and determine grouping strategy.",
        "current_goal": "Analyze images to identify their content and determine grouping categories",
        "tool": "describe_image",
        "args": {"image_path": "assets/images/first_image.jpg", "question": "What animal or object is shown in this image?"},
        "is_critical": False
    }
})}

**Example Finish:**
{json.dumps({
    "decision": "finish",
    "comment": "I have successfully created the file 'hello.txt' with the content 'Hello, World!'"
})}

**Example Error:**
{json.dumps({
    "decision": "error",
    "comment": "The file 'non_existent_file.txt' was not found."
})}

Now, analyze the conversation history and generate the appropriate JSON response.
"""

def get_reflexion_prompt_with_tools(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool, error_observation: str, tool_docs: str, relevant_memories: list = None) -> str:
    """
    Enhanced reflexion prompt that includes detailed tool documentation when tool errors are detected.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    if voice_input_enabled:
        persona = "You are voice enabled."
    else:
        persona = "You are text-based."
    
    # Include relevant memories if available
    memory_context = ""
    if relevant_memories:
        memory_context = "\n**Relevant Past Experiences:**\n"
        for i, memory in enumerate(relevant_memories[:3], 1):  # Limit to 3 most relevant
            memory_context += f"{i}. {memory}\n"
        memory_context += "\nUse these past experiences to avoid repeating the same mistakes and learn from previous tool errors.\n"

    return f"""You are a ReAct-style agent. You have just performed an action that resulted in a TOOL ERROR.

{persona}

**Current Goal:**
{current_goal}

**Original User Request:**
{original_user_request}

**Last Error Observation:**
{error_observation}
{memory_context}
**Conversation History:**
{history_str}

**TOOL ERROR DETECTED!** The last action used an invalid tool name or wrong parameters.

**AVAILABLE TOOLS AND CORRECT USAGE:**
{tool_docs}

**CRITICAL INSTRUCTIONS:**
- The error shows you tried to use a tool that doesn't exist or used wrong parameters
- You MUST use ONLY the tools listed above with their EXACT parameter names
- For image analysis, use "describe_image" with parameters: image_path, question
- For finding similar images, use "find_similar_images" with parameters: image_path, search_directory, top_k, threshold
- DO NOT invent tool names like "show_image", "read_image", "open_image" - they don't exist!

Your task is to analyze the error and decide what to do next. You have three choices for the 'decision' key:

1.  **"continue"**: Fix the error by using the correct tool and parameters from the documentation above.
    *   **"comment"**: Explain what went wrong and how you'll fix it.
    *   **"next_action"**: The corrected action with proper tool name and parameters in this EXACT format:
        {{
            "thought": "explanation of what you're trying to do",
            "current_goal": "updated goal for this step",
            "tool": "tool_name_here",
            "args": {{"parameter1": "value1", "parameter2": "value2"}},
            "is_critical": true/false (true for write_file, rm/delete commands; false for read/list operations)
        }}

2.  **"finish"**: If you cannot complete the task with available tools.
    *   **"comment"**: Explanation of why the task cannot be completed.

3.  **"error"**: If there's an unrecoverable error.
    *   **"comment"**: Description of the error.

Return your response as JSON.
"""


def get_final_summary_prompt(plan_results: list) -> str:
    """
    Generates a prompt for the LLM to respond to user prompt using the results of an executed plan.
    """
    results_str = "\n".join([f"Step {i+1} ({r['tool']}): {r['status']}\nOutput: {r['output']}" for i, r in enumerate(plan_results)])

    return f"""
You are a helpful assistant. A plan was just executed with the following results.
Your task is to provide an ultimate response to the user prompt using the result of the plan execution.

**Execution Results:**
{results_str}
"""

def get_final_summary_system_prompt():
    """
    Returns a system prompt specifically for generating a final summary of a plan's execution.
    """
    return "You are a helpful assistant. Summarize the plan execution results in a CONCISE text format. STICK to no more than 3 sentences.\
    Focus on the overall outcome and any important details or errors. If no plan was executed, provide a response based on the conversation."
