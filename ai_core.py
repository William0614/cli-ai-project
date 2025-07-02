import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompts import get_agent_system_prompt, get_summarizer_system_prompt, get_tool_summary_prompt, get_final_summary_system_prompt
import memory_system as memory

load_dotenv()

# Create an async client pointing to your local server
client = AsyncOpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-needed"
)

<<<<<<< HEAD
async def get_agent_decision(history: list, current_working_directory: str, force_text_response: bool = False) -> dict:
    """Gets the agent's decision on how to proceed based on conversation history and current working directory."""
    if force_text_response:
        system_prompt = get_final_summary_system_prompt()
        user_message = history[-1]
    else:
        recalled_memories = memory.recall_memories(history[-1])
        system_prompt = get_agent_system_prompt(history, current_working_directory, recalled_memories)
        user_message = history[-1] # Pass the latest user message
=======
async def get_agent_decision(prompt: str) -> dict:
    """Gets the agent's decision on how to proceed."""
    system_prompt = f"""
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
    """
>>>>>>> 7abea45 (fix bug)

    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"} if not force_text_response else None,
        )
        
        if force_text_response:
            decision = {"text": response.choices[0].message.content.strip()}
        else:
            decision = json.loads(response.choices[0].message.content)
        
        # Decide whether to save the conversation to memory
        if not force_text_response and "save_to_memory" in decision:
            memory.save_memory(decision["save_to_memory"], {"type": "declarative"})

        return decision

    except Exception as e:
        print(f"Error getting agent decision: {e}")
        return {"text": "Sorry, an error occurred."}

async def summarize_tool_result(tool_name: str, tool_args: dict, tool_output: dict) -> str:
<<<<<<< HEAD
    """Asks the LLM to generate a user-friendly summary of a tool's execution result."""
    summarizer_prompt = get_tool_summary_prompt(tool_name, tool_args, tool_output)
    system_prompt = get_summarizer_system_prompt()

=======
    """
    Asks the LLM to generate a user-friendly summary of a tool's execution result.
    """
    prompt = f"""
    A tool has just been executed. Please generate a brief, user-friendly sentence
    explaining the outcome. Be concise and clear.

    Tool Name: {tool_name}
    Arguments Used: {json.dumps(tool_args)}
    Raw Output: {json.dumps(tool_output)}
    """
>>>>>>> 7abea45 (fix bug)
    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": summarizer_prompt}
            ],
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"