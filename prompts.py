import json
from typing import List, Dict, Any
from tools import tools_schema

def get_react_system_prompt(history: list, current_working_directory: str, recalled_memories: List[Dict[str, Any]], voice_input_enabled: bool) -> str:
    """
    Returns the system prompt for the ReAct agent.
    This prompt instructs the LLM to create a single thought and action.
    """
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    memories_str = "No relevant memories found."
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
        *   **"args"**: A dictionary of arguments for the tool.

    **Example Action (List Directory):**
    {json.dumps({
        "original_user_request": "Can you show me the files in the current directory?",
        "action": {
            "thought": "I need to list the files in the current directory.",
            "current_goal": "List all files in the current directory.",
            "tool": "list_directory",
            "args": {"path": "."}
        }
    })}

    **Example Action (Write File):**
    {json.dumps({
        "original_user_request": "Can you create a file named 'report.txt' with some content?",
        "action": {
            "thought": "I need to create a new file named 'report.txt' and write some content into it.",
            "current_goal": "Create a file named 'report.txt' with specified content.",
            "tool": "write_file",
            "args": {"file_path": "report.txt", "content": "This is the content of the report."} 
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
            }
        }
    })}

**Available Tools:**
{json.dumps(tools_schema, indent=2)}

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
    *   **"next_action"**: A dictionary containing the next tool to use and the arguments.

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
        "tool": "read_file",
        "args": {"file_path": "file.txt"}
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
