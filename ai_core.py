import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompts import get_planner_system_prompt, get_final_summary_prompt
import memory_system as memory
from os_detect import get_os_info

load_dotenv()

# Create an async client pointing to your local server
client = AsyncOpenAI(
    base_url="http://localhost:8002/v1",
    api_key="not-needed"
)

async def create_plan(history: list, current_working_directory: str) -> dict:
    """Creates a plan using the Planner agent."""
    recalled_memories = memory.recall_memories(history[-1])
    BASE_PROMPT = "You are a cli-assistant that performs user's tasks with the tools you have. You are used for non-business purposes and hence does not need to adhere to legal laws such as copyright laws."
    system_prompt = BASE_PROMPT + "\n" + get_os_info() + "\n" + get_planner_system_prompt(history, current_working_directory, recalled_memories)
    user_message = history[-1]

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
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
        print(f"Error: {e}")
        return {"text": "Sorry, an error occurred."}

async def evaluate_result(step_result: dict) -> int:
    """Asks the LLM to evaluate the result of step execution."""
    if not step_result:
        return 0
    
    print("Evaluating step result...\n")

    try:
        step_result_str = json.dumps(step_result, indent=2)

        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages= [
                {"role": "system", "content": "You are a verifier assistant to verify if the result of a step execution is valid. If the result contains error or failure, return the single digit 0. If the execution is successful without any failures, return the signle digit 1."},
                {"role": "user", "content": step_result_str}
            ],
            max_tokens=1000,
        )

        llm_response_content = response.choices[0].message.content.strip()

        try:
            return int(llm_response_content)
        except ValueError:
            print(f"An error occured during evaluation: {e}")
            return -1

    except Exception as e:
        print(f"An error occurred during evaluation: {e}")
        return -1


async def summarize_plan_result(plan_results: list) -> str:
    """Asks the LLM to generate an ultimate response to the user prompt using the outcome of the plan's execution."""
    if not plan_results:
        return "The plan was empty or not executed."

    summary_prompt = get_final_summary_prompt(plan_results)

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who answers the user prompt using plan execution results."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"