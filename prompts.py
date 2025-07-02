


import json
from tools import tools_schema

def get_agent_system_prompt(history: list) -> str:
    """
    Returns the primary system prompt for the autonomous agent, including conversation history.
    """
    history_str = "\n".join(history)
    return f"""
You are an expert autonomous agent. Your job is to analyze a user's request,
review the conversation history, and decide on the best single next action.

**Conversation History:**
{history_str}

**Your Task:**
Based on the history and the user's latest request, decide on one of the following:

1.  **Text Response:** If the user's request is a simple question, a greeting, or can be answered directly without needing to use any tools, respond with a JSON object containing your text answer.
    Example: {{\"text\": \"Hello! How can I help you today?\"}}
    Example: {{\"text\": \"You are currently in the directory: /Users/kimboyoon/Desktop/cli-ai-project\"}}

2.  **Tool Call:** If the next logical step is to use a tool to gather information or perform an action, respond with a JSON object for that single tool call.
    Example: {{\"tool_call\": {{\"name\": \"read_file\", \"arguments\": {{\"file_path\": \"/path/to/file\"}}}}}}

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
    return prompt
