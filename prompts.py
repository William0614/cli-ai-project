import json
from typing import List, Dict, Any
from tools import tools_schema, get_tool_docstrings

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

    return f"""You are an expert autonomous agent that functions as a ReAct-style agent.
Your primary role is to analyze a user's request and the conversation history, and then decide on the single next best action to take.

{persona}

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memories_str}

**Conversation History:**
{history_str}

**Your Task:**
Based on the user's latest request and the conversation history, generate a JSON object with your thought and the next action to take. You have three choices for the top-level key in the JSON response:

1.  **"text"**: If the user's request is a simple question, a greeting, or can be answered directly without tools, use this key. The value should be the response string.
    Example: {json.dumps({"text": "Hello! How can I help you today?"})}

2.  **"save_to_memory"**: If the user provides a new piece of information that should be remembered, use this key. The value should be the string of information to save.
    Example: {json.dumps({"save_to_memory": "The user's favorite color is blue."})}

3.  **"action" and "original_user_request"**: If the request requires a tool, your JSON response **MUST** cotain these two top-level keys.  
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
            "current_goal": "List all files in the current directory.",
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

def get_reflexion_prompt(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool) -> str:
    """
    Generates a prompt for the LLM to reflect on the result of an action.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    if voice_input_enabled:
        persona = "You are voice enabled."
    else:
        persona = "You are text-based."

    return f"""You are a ReAct-style agent. You have just performed an action and observed the result.

{persona}

**Current Goal:**
{current_goal}

**Original User Request:**
{original_user_request}

**Conversation History:**
{history_str}

Your task is to analyze the observation in conversation history and decide whether the user request has been fulfilled or if further action is needed.
If the observation is from a `run_shell_command`, you should parse the `stdout` to find the relevant information. 
If the original user request has been fully addressed and completed, you MUST return 'finish'. You have three choices for the 'decision' key in your JSON response:

1.  **"continue"**: If the task is not yet complete and you need to perform another action.
    *   **"comment"**: A brief explanation of why you are continuing and what you plan to do next.
    *   **"next_action"**: A dictionary containing the next tool to use and the arguments. **MUST include "is_critical" field:**
        *   `write_file`: Always `true`.
        *   `run_shell_command`: `true` if the command modifies the system or data (e.g., `rm`, `sudo`, `mv`, `delete`, `format`, `kill`, `reboot`, `shutdown`, `apt remove`, `npm uninstall`, `pip uninstall`, `git commit`, `git push`). Otherwise, `false` (e.g., `ls`, `pwd`, `echo`, `git status`, `git log`).
        *   All other tools (`read_file`, `list_directory`, `describe_image`, `find_similar_images`): Always `false`.

2.  **"finish"**: If the task is complete and you have the final answer for the user.
    *   **"comment"**: The final answer for the user.

3.  **"error"**: If the last action resulted in an error that you cannot recover from.
    *   **"comment"**: A brief explanation of the error.

**Example Continue:**
{json.dumps({
    "decision": "continue",
    "comment": "I have listed the files. Now I need to read the content of 'file.txt'.",
    "next_action": {
        "thought": "Read the content of 'file.txt'.",
        "tool": "read_text_file",
        "args": {"file_path": "file.txt"},
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

def get_reflexion_prompt_with_tools(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool, error_observation: str, tool_docs: str) -> str:
    """
    Enhanced reflexion prompt that includes detailed tool documentation when tool errors are detected.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    if voice_input_enabled:
        persona = "You are voice enabled."
    else:
        persona = "You are text-based."

    return f"""You are a ReAct-style agent. You have just performed an action that resulted in a TOOL ERROR.

{persona}

**Current Goal:**
{current_goal}

**Original User Request:**
{original_user_request}

**Last Error Observation:**
{error_observation}

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
