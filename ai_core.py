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

async def get_agent_decision(
    conversation_history: list,
    initial_user_prompt: str,
    task_scratchpad: list,
    current_working_directory: str
) -> dict:
    """
    Gets the agent's next decision in a reasoning loop.

    The agent will decide whether to call a tool or provide a final answer based on the task and its scratchpad.

    Args:
        conversation_history: High-level history of user/agent interactions.
        initial_user_prompt: The specific goal for the current task.
        task_scratchpad: The history of thoughts, actions, and observations for the current task.
        current_working_directory: The agent's current CWD.

    Returns:
        A dictionary containing either a "tool_call" or a "final_answer".
    """
    # 1. Recall long-term memories relevant to the main goal
    recalled_memories = memory.recall_memories(initial_user_prompt)
    #recalled_memories = ""
    # 2. Get the system prompt (this needs to be updated in prompts.py)
    # It now contains the core instructions for the reasoning loop.
    system_prompt = get_agent_system_prompt(current_working_directory,conversation_history, initial_user_prompt, task_scratchpad, recalled_memories)

    # 3. Construct the user message with all the dynamic context for this step
    user_content = f"""
    Current Working Directory: {current_working_directory}

    Conversation History (for context):
    {conversation_history}

    ---
    CURRENT TASK
    ---

    User's Goal: "{initial_user_prompt}"

    Your Scratchpad (your thoughts and actions so far for this task):
    {''.join(task_scratchpad) if task_scratchpad else "No steps taken yet. This is your first thought."}

    ---
    INSTRUCTION
    ---
    Based on the user's goal and your scratchpad, decide on your next action.
    Do you need to use a tool, or are you ready to give the final answer?
    Respond with a single JSON object.
    """

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        decision = json.loads(response.choices[0].message.content)
        return decision

    except Exception as e:
        print(f"Error getting agent decision: {e}")
        # Return a structured error that the main loop can handle
        return {"final_answer": f"Sorry, an error occurred while I was thinking: {e}"}

async def summarize_tool_result(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    """Asks the LLM to generate a user-friendly summary of a tool's execution result."""
    summarizer_prompt = get_tool_summary_prompt(tool_name, tool_args, tool_output)
    system_prompt = get_summarizer_system_prompt()

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": summarizer_prompt}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"

async def verify_agent_plan(initial_user_prompt: str, task_scratchpad: list, proposed_plan: list) -> dict:
    """
    Calls a supervisor LLM to check if a proposed plan is logical, safe, and effective.
    
    Returns a dictionary with a decision: 'APPROVE', 'DECLINE', or 'CONFIRM_CRITICAL'.
    """
    
    system_prompt = """
    You are a meticulous and cautious AI assistant supervisor. Your role is to review a plan of tool calls proposed by another AI agent. Your primary duty is to ensure the plan is logical, safe, and directly helps achieve the user's ultimate goal. You MUST respond with a single JSON object.

    You will be given the user's goal, the agent's work history (scratchpad), and the agent's proposed plan.

    Analyze the plan and choose one of three possible decisions:

    1.  **APPROVE**: The plan is logical, safe, and a clear step towards the user's goal.
        - Example: The user wants to read a file, and the plan is `[{"name": "read_file", "parameters": {"file_path": "file.txt"}}]`. This is a good plan.
        - JSON Output: `{"decision": "APPROVE"}`

    2.  **DECLINE**: The plan is illogical, incorrect, hallucinates tool usage, or is inefficient. It will not help solve the user's goal.
        - Example: The user wants to list files, but the plan is `[{"name": "write_file", "parameters": {}}]`. This is wrong.
        - JSON Output: `{"decision": "DECLINE", "reason": "The plan uses the wrong tool. It should use 'list_directory' not 'write_file'."}`

    3.  **CONFIRM_CRITICAL**: The plan includes a potentially dangerous or irreversible action. This requires human confirmation.
        - CRITICAL actions include: deleting files (`delete_file`), running destructive shell commands (`rm`, `mv`), or overwriting important existing files.
        - Example: The plan is `[{"name": "delete_file", "parameters": {"file_path": "config.json"}}]`. This is dangerous.
        - JSON Output: `{"decision": "CONFIRM_CRITICAL", "reason": "The plan proposes to delete a file, which is an irreversible action."}`

    Your response MUST be a single JSON object with a "decision" key and an optional "reason" key. Do not add any other text.
    """

    formatted_scratchpad = "\n".join(task_scratchpad) if task_scratchpad else "No actions taken yet."
    formatted_plan = json.dumps(proposed_plan, indent=2)

    user_content = f"""
    **User's Ultimate Goal:**
    {initial_user_prompt}

    **Agent's Work History (Scratchpad):**
    ```
    {formatted_scratchpad}
    ```

    **Agent's Proposed Plan to Execute Next:**
    ```json
    {formatted_plan}
    ```

    Review the proposed plan based on the goal and history. Is it logical and safe? Provide your decision as a single JSON object.
    """

    try:
        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder32B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        
        decision = json.loads(response.choices[0].message.content)
        if 'decision' not in decision or decision['decision'] not in ['APPROVE', 'DECLINE', 'CONFIRM_CRITICAL']:
             raise ValueError("Verifier returned an invalid decision format.")
        return decision

    except Exception as e:
        print(f"{Fore.RED}Error getting plan verification: {e}")
        # Fail-safe: If the verifier fails, default to requiring human confirmation.
        return {
            "decision": "CONFIRM_CRITICAL",
            "reason": f"The AI verifier failed with an error: {e}. Please review the plan carefully."
        }