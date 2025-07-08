import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompts import get_planner_system_prompt, get_final_summary_prompt
import memory_system as memory

load_dotenv()

# Create an async client pointing to your local server
client = AsyncOpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-needed"
)

async def create_plan(history: list, current_working_directory: str) -> dict:
    """Creates a plan using the Planner agent."""
    recalled_memories = memory.recall_memories(history[-1])
    system_prompt = get_planner_system_prompt(history, current_working_directory, recalled_memories)
    user_message = history[-1]

    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        decision = json.loads(response.choices[0].message.content)
        
        if "save_to_memory" in decision:
            memory.save_memory(decision["save_to_memory"], {"type": "declarative"})

        return decision

    except Exception as e:
        print(f"Error creating plan: {e}")
        return {"text": "Sorry, an error occurred while creating a plan."}

async def summarize_plan_result(plan_results: list) -> str:
    """Asks the LLM to generate a final summary of the plan's execution."""
    if not plan_results:
        return "The plan was empty or not executed."

    summary_prompt = get_final_summary_prompt(plan_results)

    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who summarizes plan execution results."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"