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

async def gather_context(user_request: str, current_working_directory: str) -> str:
    """Step 2: Gathers context from the environment based on the user's request.
    This is a placeholder. Actual implementation would involve using tools like glob, list_directory, read_file.
    """
    # In a real scenario, this would involve LLM calls or tool usage to gather relevant info.
    # For now, it's a placeholder.
    print(f"\n--- Step 2: Gathering Context for request: {user_request} ---")
    # Example: You might use tools here to list files, read relevant configs, etc.
    # For instance, if the request is about a file, you might read its content.
    # context_info = await read_file_tool(file_path_derived_from_request)
    return "" # Return gathered context as a string or structured data

async def create_plan(history: list, current_working_directory: str, gathered_context: str) -> dict:
    """Step 3: Creates a plan using the Planner agent, incorporating gathered context."""
    recalled_memories = memory.recall_memories(history[-1])
    system_prompt = get_planner_system_prompt(history, current_working_directory, recalled_memories, gathered_context)
    user_message = history[-1]

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
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
    """Asks the LLM to generate an ultimate response to the user prompt using the outcome of the plan's execution."""
    if not plan_results:
        return "The plan was empty or not executed."

    summary_prompt = get_final_summary_prompt(plan_results)

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who answers the user prompt using plan execution results."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"