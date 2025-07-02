
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools import tools_schema

load_dotenv()

client = AsyncOpenAI(
    base_url=os.getenv("LOCAL_LLM_URL"),
    api_key='ollama',
)

async def get_agent_decision(prompt: str) -> dict:
    """Gets the agent's decision on how to proceed."""
    # ... (this function remains the same as before)
    system_prompt = f""""
    You are an expert autonomous agent. Your job is to analyze a user's request
    and decide on the best course of action.

    **IMPORTANT SAFETY RULE:**
    You must prioritize using specific, safe tools (e.g., `read_file`, `write_file`) over the general-purpose `run_shell_command`.
    Only use `run_shell_command` for simple, non-destructive commands when no specific tool is available for the task (e.g., getting the current date).
    For any file creation, deletion, or modification, you MUST use the dedicated file system tools.

    You have three choices:

    1.  If the request is simple and can be handled by a single tool call, respond with a JSON object containing a single key, "tool_call", which contains the details of the function to call.
        Example: {{"tool_call": {{"name": "read_file", "arguments": {{"file_path": "/path/to/file"}}}}}}

    2.  If the request is complex and requires multiple steps, respond with a JSON object containing a single key, "plan", which is a list of tool call steps.
        Example: {{"plan": [ {{"name": "read_file", ...}}, {{"name": "write_file", ...}} ]}}

    3.  If the request is a simple question or greeting that doesn't require a tool, respond with a JSON object containing a single key, "text", with your response.
        Example: {{"text": "Hello! How can I help you today?"}}

    Here are the available tools:
    {json.dumps(tools_schema, indent=2)}
    """"

    try:
        response = await client.chat.completions.create(
            model="deepseek-coder-v2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, # Force JSON output
        )
        
        decision = json.loads(response.choices[0].message.content)
        return decision

    except Exception as e:
        print(f"Error getting agent decision: {e}")
        return {"text": "Sorry, an error occurred."}

async def summarize_tool_result(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    """
    Asks the LLM to generate a user-friendly summary of a tool's execution result.
    """
    prompt = f""""
    A tool has just been executed. Please generate a brief, user-friendly sentence
    explaining the outcome. Be concise and clear.

    Tool Name: {tool_name}
    Arguments Used: {json.dumps(tool_args)}
    Raw Output: {json.dumps(tool_output)}
    """"
    try:
        response = await client.chat.completions.create(
            model="deepseek-coder-v2",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who summarizes technical output for a user."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"
