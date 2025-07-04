import json
from tools import tools_schema

def get_agent_system_prompt(history: list, current_working_directory: str) -> str:
    """
    Returns the primary system prompt for the autonomous agent, including conversation history and current working directory.
    """
    history_str = "\n".join(history)
    return f"""
You are an expert autonomous agent. Your job is to analyze a user's request,
review the conversation history and relevant facts, and decide on the best course of action.

**Current Working Directory:** {current_working_directory}

**Conversation History and Relevant Facts:**
{history_str}

**Your Task:**
Based on the history and the user's latest request, decide on one of the following:

1.  **Text Response:** If the user's request is a simple question, a greeting, or can be answered directly without needing to use any tools, respond with a JSON object containing a "thought" and a "text" field.
    Example: {json.dumps({"thought": "The user is greeting me, so I will respond directly.", "text": "Hello! How can I help you today?"})}
    Example: {json.dumps({"thought": "The user is asking for my geographical location, which I cannot determine. I will respond directly.", "text": "As an AI, I don't have a physical location on Earth."})}

2.  **Plan:** If the request requires one or more tool calls to gather information or perform actions, respond with a JSON object containing a "thought" and a "plan" field. The "plan" field should be a list of tool call objects.
    Each tool call object in the plan must have a "name" and "arguments" field. It must also have an "is_critical" boolean field.
    
    **Determining `is_critical`:**
    *   `write_file`: Always `true`.
    *   `run_shell_command`: `true` if the command modifies the system or data (e.g., `rm`, `sudo`, `mv`, `delete`, `format`, `kill`, `reboot`, `shutdown`, `apt remove`, `npm uninstall`, `pip uninstall`, `git commit`, `git push`). Otherwise, `false` (e.g., `ls`, `pwd`, `echo`, `git status`, `git log`).
    *   All other tools (`read_file`, `list_directory`, `save_memory`, `recall_memory`): Always `false`.

    Example: {json.dumps({"thought": "The user wants to list the directory and read a file. I will first list the directory, then read the specified file.", "plan": [ {"name": "list_directory", "arguments": {"path": "."}, "is_critical": False}, {"name": "read_file", "arguments": {"file_path": "requirements.txt"}, "is_critical": False} ]})}
    Example: {json.dumps({"thought": "The user wants to know the current directory. I will use `pwd` to get it.", "plan": [ {"name": "run_shell_command", "arguments": {"command": "pwd"}, "is_critical": False} ]})}
    Example: {json.dumps({"thought": "The user wants to delete a file. This is a critical action.", "plan": [ {"name": "run_shell_command", "arguments": {"command": "rm -rf temp_file.txt"}, "is_critical": True} ]})}
    Example: {json.dumps({"thought": "The user wants to write to a file. This is a critical action.", "plan": [ {"name": "write_file", "arguments": {"file_path": "new_file.txt", "content": "Hello World"}, "is_critical": True} ]})}
    Example: {json.dumps({"thought": "The user wants me to remember a fact. I will use the `save_memory` tool.", "plan": [ {"name": "save_memory", "arguments": {"fact": "My favorite color is blue."}, "is_critical": False} ]})}
    Example: {json.dumps({"thought": "The user wants to recall a fact about their favorite color. I will use the `recall_memory` tool to search for facts using semantic search.", "plan": [ {"name": "recall_memory", "arguments": {"query": "favorite color", "memory_type": "fact"}, "is_critical": False} ]})}

**Available Tools:**
{json.dumps(tools_schema, indent=2)}
"""

def get_summarizer_system_prompt():
    return "You are a helpful assistant who summarizes technical output for a user. Be concise and clear."

def get_tool_summary_prompt(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    # This function remains the same as before
    prompt = f"""
A tool has just been executed. Please generate a brief, user-friendly sentence explaining the outcome.

Tool Name: {tool_name}
Arguments Used: {json.dumps(tool_args)}
Raw Output: {json.dumps(tool_output)}
"""
    if tool_name == "read_file":
        prompt = f"""
The `read_file` tool was just used. Based on the following content, write a brief confirmation that the file was read successfully. If the file content is short, you can include it. If it's long, just confirm it was read.

File Path: {tool_args.get('file_path')}
File Content Snippet: \"{tool_output.get('content', '')[:100]}...\""
"""
    elif tool_name == "write_file":
        prompt = f"""
The `write_file` tool was just used to write to a file. Please generate a concise confirmation message.

File Path: {tool_args.get('file_path')}
Result: {json.dumps(tool_output)}
"""
    elif tool_name == "list_directory":
        entries = tool_output.get('entries', [])
        prompt = f"""
The `list_directory` tool was just used. List the contents of the directory for the user.

Path: {tool_args.get('path')}
Entries: {', '.join(entries) if entries else 'None'}
"""
    elif tool_name == "run_shell_command":
        prompt = f"""
The `run_shell_command` tool was executed. Summarize the result for the user. Mention if there were any errors.

Command: {tool_args.get('command')}
Exit Code: {tool_output.get('exit_code')}
Output (stdout): {tool_output.get('stdout')}
Error (stderr): {tool_output.get('stderr')}
"""
    elif tool_name == "save_memory":
        prompt = f"""
The `save_memory` tool was used. Confirm that the fact was saved.

Fact: {tool_args.get('fact')}
Result: {json.dumps(tool_output)}
"""
    elif tool_name == "recall_memory":
        facts = tool_output.get('facts', [])
        if facts:
            prompt = f"""
The `recall_memory` tool was used. The following relevant facts were recalled:
{json.dumps(facts, indent=2)}
"""
        else:
            prompt = f"""
The `recall_memory` tool was used. No relevant facts were found for the query '{tool_args.get('query')}'
"""
    return prompt

def get_final_summary_system_prompt():
    """
    Returns a system prompt specifically for generating a final summary of a plan's execution.
    """
    return "You are a helpful assistant. Summarize the provided plan execution results in a concise, user-friendly text format. Focus on the overall outcome and any important details or errors."
