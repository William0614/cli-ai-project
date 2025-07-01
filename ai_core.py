import os
import asyncio
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
# Import the function definitions from tools.py
# This is how the model knows what functions it can call.
from tools import tools_schema

load_dotenv()

# Create an async client pointing to your local server
client = AsyncOpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-needed"
)

async def get_ai_decision(prompt: str) -> dict:
    """
    Asks the LLM to decide the best course of action for a given prompt.
    """
    system_prompt = f"""
    You are an expert autonomous agent. Your job is to analyze a user's request and decide on the best course of action.
    You have three choices:

    1. If the request is simple and can be handled by a single tool call, respond with a JSON object containing a single key, "tool_call", which contains the details of the function to call.
    Example: {{"tool_call": {{"name": "read_file", "arguments": {{"file_path": "/path/to/file"}}}}}}

    2. If the request is complex and requires multiple steps, respond with a JSON object containing a single key, "plan", which is a list of tool call steps.
    Example: {{"plan": [ {{"name": "read_file", ...}}, {{"name": "write_file", ...}} ]}}

    3. If the request is a simple question or greeting that doesn't require a tool, respond with a JSON object containing a single key, "text", with your response.
    Example: {{"text": "Hello! How can I help you today?"}}

    Here are the available tools: {json.dumps(tools_schema, indent=2)}
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