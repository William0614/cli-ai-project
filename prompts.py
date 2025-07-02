
import json
from tools import tools_schema

def get_agent_system_prompt():
    """
    Returns the primary system prompt for the autonomous agent.
    This prompt guides the agent in making decisions (planning, single actions, or simple text responses).
    """
    return f"""
You are an expert autonomous agent. Your job is to analyze a user's request and decide on the best course of action.

**IMPORTANT SAFETY RULE:**
You must prioritize using specific, safe tools (e.g., `read_file`, `write_file`) over the general-purpose `run_shell_command`.
Only use `run_shell_command` for simple, non-destructive commands when no specific tool is available for the task (e.g., getting the current date).
For any file creation, deletion, or modification, you MUST use the dedicated file system tools.

You have three choices:

1.  **Plan:** If the request is complex and requires multiple steps, respond with a JSON object containing a single key, "plan", which is a list of tool call steps.
    Example: {{"plan": [ {{"name": "read_file", ...}}, {{"name": "write_file", ...}} ]}}

2.  **Tool Call:** If the request can be handled by a single tool call, respond with a JSON object containing a single key, "tool_call", with the function details.
    Example: {{"tool_call": {{"name": "read_file", "arguments": {{"file_path": "/path/to/file"}}}}}}

3.  **Text:** If the request is a simple question or greeting that doesn't require a tool, respond with a JSON object containing a single key, "text".
    Example: {{"text": "Hello! How can I help you today?"}}

Here are the available tools:
{json.dumps(tools_schema, indent=2)}
"""

def get_summarizer_system_prompt():
    """
    Returns the system prompt for the summarizer AI.
    This is a generic fallback for tools without a specific summarizer.
    """
    return "You are a helpful assistant who summarizes technical output for a user. Be concise and clear."

def get_tool_summary_prompt(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    """
    Generates a specific prompt for the LLM to summarize a tool's result based on the tool name.
    """
    # Default prompt for any tool not specifically handled
    prompt = f"""
A tool has just been executed. Please generate a brief, user-friendly sentence explaining the outcome.

Tool Name: {tool_name}
Arguments Used: {json.dumps(tool_args)}
Raw Output: {json.dumps(tool_output)}
"""

    # Specific prompts for each tool
    if tool_name == "read_file":
        prompt = f"""
The `read_file` tool was just used. Based on the following content, write a brief confirmation that the file was read successfully. If the file content is short, you can include it. If it's long, just confirm it was read.

File Path: {tool_args.get('file_path')}
File Content Snippet: "{tool_output.get('content', '')[:100]}..."
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
