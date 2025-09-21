import json
from typing import List, Dict, Any, Optional
from ..tools.tools import tools_schema, get_tool_docstrings


# Task memory for preventing redundant actions within a task
_current_task_memory = {
    "task_id": None,
    "original_request": "",
    "actions_taken": [],
    "knowledge": {},
    "current_goal": ""
}


def reset_task_memory(task_description: str = ""):
    """Reset task memory for a new task."""
    global _current_task_memory
    _current_task_memory = {
        "task_id": f"task_{len(_current_task_memory.get('actions_taken', []))}",
        "original_request": task_description,
        "actions_taken": [],
        "knowledge": {},
        "current_goal": ""
    }


def add_action_to_memory(tool: str, args: dict, thought: str, goal: str, result: dict = None):
    """Add an action to the current task memory."""
    action = {
        "tool": tool,
        "args": args,
        "thought": thought,
        "goal": goal,
        "result": result,
        "timestamp": "now"  # Would be datetime in real implementation
    }
    _current_task_memory["actions_taken"].append(action)
    _current_task_memory["current_goal"] = goal


def update_task_knowledge(key: str, value: Any):
    """Update accumulated knowledge for the current task."""
    _current_task_memory["knowledge"][key] = value


def get_task_context_string() -> str:
    """Get a formatted string of current task context."""
    if not _current_task_memory["actions_taken"]:
        return "No actions taken yet in this task."
    
    context = f"Task: {_current_task_memory['original_request']}\n"
    context += f"Current Goal: {_current_task_memory['current_goal']}\n"
    context += f"Actions Taken: {len(_current_task_memory['actions_taken'])}\n"
    
    if _current_task_memory["knowledge"]:
        context += "Knowledge Accumulated:\n"
        for key, value in _current_task_memory["knowledge"].items():
            context += f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}\n"
    
    # Show recent actions to prevent redundancy
    recent_actions = _current_task_memory["actions_taken"][-3:] if _current_task_memory["actions_taken"] else []
    if recent_actions:
        context += "Recent Actions:\n"
        for i, action in enumerate(recent_actions, 1):
            context += f"  {i}. {action['tool']}({action['args']}) - {action['thought']}\n"
    
    return context


def has_performed_action(tool: str, args: dict = None) -> bool:
    """Check if a similar action has already been performed in this task."""
    for action in _current_task_memory["actions_taken"]:
        if action["tool"] == tool:
            if args is None or action["args"] == args:
                return True
    return False

def get_react_system_prompt(history: list, current_working_directory: str, recalled_memories: List[Dict[str, Any]], voice_input_enabled: bool) -> str:
    """
    Returns the system prompt for the ReAct agent.
    This prompt instructs the LLM to create a single thought and action.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    memories_str = ""
    if recalled_memories:
        memories_list = [f"- {m['content']} (timestamp: {m['timestamp']})" for m in recalled_memories]
        memories_str = "\n".join(memories_list)
    if voice_input_enabled:
        persona = "You are voice enabled. You interact with the user by speaking aloud. When you provide information or ask a question, you are speaking directly to them."
    else:
        persona = "You interact with the user through command line text interface."

    # Add task context to prevent redundant actions
    task_context = get_task_context_string()

    return f"""You are an expert autonomous agent that functions as a ReAct-style agent.
Your primary role is to analyze a user's request and the conversation history, and then decide on the single next best action to take.

{persona}

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memories_str}

**Task Context (to prevent redundant actions):**
{task_context}

**Conversation History:**
{history_str}

**Your Task:**
Based on the user's latest request and the conversation history, generate a JSON object with your thought and the next action to take. 

**IMPORTANT: Before choosing a tool, consider:**
1. What exactly does the user want to achieve?
2. What tools are available to me?
3. What is the logical sequence of steps needed?
4. Which tool should I use for the NEXT step?

**IMPORTANT: If a user request is ambiguous or lacks necessary details, ask for clarification using the "text" response. Keep clarification questions short and natural.**

You have two choices for the top-level key in the JSON response:

1.  **"text"**: If the user's request is a simple question, a greeting, or can be answered directly without tools, use this key. The value should be the response string.
    Example: {json.dumps({"text": "Hello! How can I help you today?"})}

2.  **"action" and "original_user_request"**: If the request requires a tool, your JSON response **MUST** cotain these two top-level keys.  
    *   **`original_user_request`**: A string containing the verbatim user prompt that initiated the current task. You must look back in the conversation history to find the root of the request, 
    especially if the last message was a clarification. The value should be a dictionary containing the tool to use and the arguments.
    *   **`action`**: A dictionary containing the following keys:
        *   **"thought"**: A brief description of what you are trying to do.
        *   **"current_goal"**: A concise statement of the specific goal this action aims to achieve. This should be a sub-goal of the overall user request.
        *   **"tool"**: The name of the tool to use. You **MUST ONLY** use the tools defined in the schema below.
        *   **"args"**: A dictionary of arguments for the tool. **USE EXACT PARAMETER NAMES FROM SCHEMA.**
        *   **"is_critical"**: (REQUIRED) A boolean field that determines if user confirmation is needed before execution.
            **Determining `is_critical`:**
            *   `write_file`: Always `true`.
            *   `run_shell_command`: `true` if the command modifies the system or data (e.g., `rm`, `sudo`, `mv`, `delete`, `format`, `kill`, `reboot`, `shutdown`, `apt remove`, `npm uninstall`, `pip uninstall`, `git commit`, `git push`). Otherwise, `false` (e.g., `ls`, `pwd`, `echo`, `git status`, `git log`).
            *   All other tools (`read_file`, `list_directory`, `describe_image`, `find_similar_images`): Always `false`.

    **Example Action (List Directory):**
    {json.dumps({
        "original_user_request": "Can you show me the files in the current directory?",
        "action": {
            "thought": "I need to list the files in the current directory.",
            "current_goal": "List all files in the current directory",
            "tool": "list_directory",
            "args": {"path": "."},
            "is_critical": False
        }
    })}

    **Example Action (Write File):**
    {json.dumps({
        "original_user_request": "Can you create a file named 'report.txt' with some content?",
        "action": {
            "thought": "I need to create a new file named 'report.txt' and write some content into it.",
            "current_goal": "Create a file named 'report.txt' with specified content.",
            "tool": "write_file",
            "args": {"file_path": "report.txt", "content": "This is the content of the report."},
            "is_critical": True
        }
    })}

    **Example Action (Delete File - CRITICAL):**
    {json.dumps({
        "original_user_request": "Please delete the old_file.txt",
        "action": {
            "thought": "I need to delete the file 'old_file.txt' as requested.",
            "current_goal": "Delete old_file.txt from the system.",
            "tool": "run_shell_command",
            "args": {"command": "rm old_file.txt"},
            "is_critical": True
        }
    })}

    **Example Action (Describe Image):**
    {json.dumps({
        "original_user_request": "What does the image abc123.jpg show?",
        "action": {
            "thought": "I need to analyze the specific image file to describe what it shows.",
            "current_goal": "Describe the content of abc123.jpg.",
            "tool": "describe_image",
            "args": {
                "image_path": "./image/abc123.jpg",
                "question": "What is in this image?"
            },
            "is_critical": False
        }
    })}

    **Example Action (Find Similar Images):**
    {json.dumps({
        "original_user_request": "Find similar images to the first image in the images folder.",
        "action": {
            "thought": "I need to find images visually similar to 'image/first_image.jpg' in the images folder.",
            "current_goal": "Find the top 5 similar images.",
            "tool": "find_similar_images",
            "args": {
                "image_path": "image/first_image.jpg",
                "search_directory": "image",
                "top_k": 5,
                "threshold": 0.5
            },
            "is_critical": False
        }
    })}

**Available Tools:**
{json.dumps(tools_schema, indent=2)}

**CRITICAL: Use ONLY the tools listed above. For images use 'describe_image' and 'find_similar_images'.**

Now, analyze the user's request and generate the appropriate JSON response.
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
