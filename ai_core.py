import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompts import get_agent_system_prompt, get_summarizer_system_prompt, get_tool_summary_prompt, get_final_summary_system_prompt

load_dotenv()

client = AsyncOpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-needed"
)

async def get_agent_decision(history: list, current_working_directory: str, force_text_response: bool = False) -> dict:
    """Gets the agent's decision on how to proceed based on conversation history and current working directory."""
    if force_text_response:
        system_prompt = get_final_summary_system_prompt()
        user_message = history[-1]
    else:
        system_prompt = get_agent_system_prompt(history, current_working_directory)
        user_message = history[-1] # Pass the latest user message

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
        return decision

    except Exception as e:
        print(f"Error getting agent decision: {e}")
        return {"text": "Sorry, an error occurred."}

async def summarize_tool_result(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    """Asks the LLM to generate a user-friendly summary of a tool's execution result."""
    summarizer_prompt = get_tool_summary_prompt(tool_name, tool_args, tool_output)
    system_prompt = get_summarizer_system_prompt()

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