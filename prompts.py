import json
from typing import List, Dict, Any
from tools import tools_schema

def get_planner_system_prompt(history: list, current_working_directory: str, recalled_memories: List[Dict[str, Any]]) -> str:
    """
    Returns the system prompt for the Planner agent.
    This prompt instructs the LLM to create a structured, multi-step plan.
    """
    history_str = "\n".join(history)
    
    memories_str = "No relevant memories found."
    if recalled_memories:
        memories_list = [f"- {m['content']} (timestamp: {m['timestamp']})" for m in recalled_memories]
        memories_str = "\n".join(memories_list)

    return f"""You are an expert autonomous agent that functions as a planner.
Your primary role is to analyze a user's request and create a comprehensive, step-by-step plan to achieve the user's goal.

**Current Working Directory:** {current_working_directory}

**Recalled Memories:**
{memories_str}

**Conversation History:**
{history_str}

**Your Task:**
Based on the user's latest request, create a JSON object that outlines the plan. You have three choices for the top-level key in the JSON response:

1.  **"text"**: If the user's request is a simple question, a greeting, or can be answered directly without tools, use this key. The value should be the response string.
    *   **Crucially, when asked about personal information (e.g., your preferences, age, name), you MUST ONLY use information present in the "Recalled Memories" section. If the information is not there, state that you don't know or don't have that information. If a recalled memory implies the answer to a question (e.g., if you know the user is a 'girl', then they are not a 'boy'), you should infer the answer.**
    Example: {json.dumps({"text": "Hello! How can I help you today?"})}

2.  **"save_to_memory"**: If the user provides a new piece of information that should be remembered, use this key. The value should be the string of information to save.
    Example: {json.dumps({"save_to_memory": "The user's favorite color is blue."})}

3.  **"plan"**: If the request requires tool usage, use this key. The value must be a list of step objects. Each step represents a single tool call and may include a checkpoint.

    **Plan Structure:**
    - A plan is a list of steps: `[step1, step2, ...]`
    - Each step is an object with:
        - `"thought"`: A brief description of the reasoning for this step.
        - `"tool"`: The name of the tool to use (e.g., "run_shell_command").
        - `"args"`: A dictionary of arguments for the tool.
        - `"is_critical"`: (boolean) `true` if the action requires user confirmation (e.g., deleting files, modifying code).
        - `"checkpoint"`: (Optional) A condition to evaluate after the tool runs. If the condition is not met, the plan execution stops. This is crucial for creating robust, adaptive plans. Checkpoints should be phrased as a question about the tool's output.

    **Checkpoint Logic:**
    - Use checkpoints to handle uncertainty. For example, before moving files, check if any were found.
    - A checkpoint is a question about the output of the current step. For example, after using `glob` to find cat images, a good checkpoint would be: "Were any cat images found?"
    - The executor will evaluate the checkpoint based on the tool's output. If the answer is no, the plan will halt.

    **Example of a Multi-Step Plan with a Checkpoint:**
    {json.dumps({
        "plan": [
            {
                "thought": "First, I need to find all the images in the 'images' directory that might be cats. I'll use glob to search for files with 'cat' in the name.",
                "tool": "glob",
                "args": {"pattern": "images/*cat*.jpg"},
                "is_critical": False,
                "checkpoint": "Were any files found?"
            },
            {
                "thought": "Now that I have a list of potential cat images, I will create a new directory called 'cats' to move them into.",
                "tool": "run_shell_command",
                "args": {"command": "mkdir cats"},
                "is_critical": True
            },
            {
                "thought": "Finally, I will move all the found images into the 'cats' directory. I will need to get the output from the first step to do this.",
                "tool": "run_shell_command",
                "args": {"command": "mv <output_of_step_1> cats/"},
                "is_critical": True
            }
        ]
    })}

**Available Tools:**
{json.dumps(tools_schema, indent=2)}

Now, analyze the user's request and generate the appropriate JSON response.
"""

def get_final_summary_prompt(plan_results: list) -> str:
    """
    Generates a prompt for the LLM to summarize the results of an executed plan.
    """
    results_str = "\n".join([f"Step {i+1} ({r['tool']}): {r['status']}\nOutput: {r['output']}" for i, r in enumerate(plan_results)])

    return f"""
You are a helpful assistant. A plan was just executed with the following results.
Your task is to provide a concise, user-friendly summary of the outcome.

**Execution Results:**
{results_str}

Based on these results, what is the final outcome?
If all steps succeeded, confirm the successful completion of the task.
If any step failed, explain what went wrong and what the final state of the system is.
"""

def get_final_summary_system_prompt():
    """
    Returns a system prompt specifically for generating a final summary of a plan's execution.
    """
    return "You are a helpful assistant. Summarize the provided plan execution results in a concise, user-friendly text format. Focus on the overall outcome and any important details or errors. If no plan was executed, provide a general, helpful response based on the conversation."
