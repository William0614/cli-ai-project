import os
import asyncio
import json
from openai import AsyncOpenAI # Import the Async client
from dotenv import load_dotenv
from tools import tools_schema

load_dotenv()

# Use the AsyncOpenAI client
client = AsyncOpenAI(
    base_url=os.getenv("http://localhost:8001/v1"),
    api_key='not-needed',
)

async def get_ai_response(prompt: str) -> dict:
    """Gets a response from the local model asynchronously."""
    try:
        # Use 'await' for the API call
        response = await client.chat.completions.create(
            model="deepsee-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[{"role": "user", "content": prompt}],
            tools=tools_schema,
            tool_choice="required",
            max_tokens=1500,
        )
        response_message = response.choices[0].message
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            return {
                "tool_name": tool_call.function.name,
                "tool_args": json.loads(tool_call.function.arguments)
            }
        else:
            return {"text": response_message.content}
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return {"text": f"Error: {e}"}