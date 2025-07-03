
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools import tools_schema
from memory import save_memory
from pathlib import Path

memory_file = Path(os.getcwd()).resolve() / ".cli_ai" / "CLI_AI.md"

load_dotenv()

client = AsyncOpenAI(

    base_url="http://localhost:8002/v1",
    api_key="not-needed"

)

async def summarise_cur_conv(cur_conv: str) -> dict:
    system_prompt = "I will give you a conversation of a user and a cli and i want you to summarise the main events and all things that changed in files(ie update the location of files).Also i need you to remember the previous user's prompt."
    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cur_conv}
            ],
            response_format= {"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result


    except Exception as e:
        print(f"Error getting agent decision: {e}")
        return {"text": "Sorry, an error occurred."}

async def get_agent_decision(prompt: str, current_path: str, cur_conv: str) -> dict:
    """Gets the agent's decision on how to proceed."""
    # ... (this function remains the same as before)
    overview = cur_conv
    if (cur_conv!= " "):
        overview = await summarise_cur_conv(cur_conv)
        print(overview)
    system_prompt = f"""
        You are an expert autonomous agent. Your job is to analyze a user's request
        and decide on the best course of action.

        **IMPORTANT SAFETY RULE:**
        You must prioritize using specific, safe tools (e.g., `read_file`, `write_file`) over the general-purpose `run_shell_command`.
        Only use `run_shell_command` for simple, non-destructive commands when no specific tool is available for the task (e.g., getting the current date).

        You have three choices:

        1. If the request is simple and can be handled by a single tool call, respond with a JSON object containing a single key, "tool_call", which contains the details of the function to call.
        Example: {{"tool_call": {{"name": "read_file", "arguments": {{"file_path": "/path/to/file"}}}}}}

        2. If the request is complex and requires multiple steps, respond with a JSON object containing a single key, "plan", which is a list of tool call steps.
        Example: {{"plan": [ {{"name": "read_file", ...}}, {{"name": "write_file", ...}} ]}}

        3. If the request is a simple question or greeting that doesn't require a tool, respond with a JSON object containing a single key, "text", with your response.
        Example: {{"text": "Hello! How can I help you today?"}}

        Please consider the following:
        - The most recent conversation context overview is: {overview}.  **Remembering Facts:** Use this to remember specific, *user-related* facts or preferences when the user explicitly asks, or when they state a clear, concise piece of information that would help personalize or streamline *your future interactions with them* (e.g., preferred coding style, common project paths they use, personal tool aliases). This tool is for user-specific information that should persist across sessions.
        - Your current path is: {current_path}. I want you to REMEMBER the current path. IT IS VERY IMPORTANT!!!! JUST IGNORE OTHER PATHS YOU SEE IN CONVERSATION HISTORY THIS IS THE ACTUAL CURRENT PATH.

        Here are the available tools:
        {json.dumps(tools_schema, indent=2)}
        """


    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
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
    """
    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who summarizes technical output for a user."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
        )
        save_memory(response.choices[0].message.content.strip())
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"
