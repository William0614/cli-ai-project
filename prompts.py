import json
from typing import List, Dict, Any
from tools import available_tools, tools_schema

import json
from typing import List, Dict, Any

# This function now requires the tools_schema to be passed in
def get_agent_system_prompt(
    current_working_directory: str,
    conversation_history: list,
    initial_user_prompt: str,
    task_scratchpad: list,
    recalled_memories: List[Dict[str, Any]],
) -> str:
    
    history_str = "\n".join(conversation_history) if conversation_history else "No conversation history yet."
    scratchpad_str = "\n".join(task_scratchpad) if task_scratchpad else "No steps taken yet for this task."
    
    num_recent_to_show = 5 
    memories_str = "No relevant memories found."
    if recalled_memories:
        sorted_memories = sorted(recalled_memories, key=lambda m: m['timestamp'], reverse=True)
        recent_memories = sorted_memories[:num_recent_to_show]
        memories_list = [f"- {m['content']} (timestamp: {m['timestamp']})" for m in recent_memories]
        memories_str = "\n".join(memories_list)

    # --- START: THE NEW, REVISED PROMPT ---
    return f"""
You are an expert autonomous agent. Your primary objective is to achieve the user's goal by breaking it down into a sequence of logical actions.

**Core Principles:**
1.  **Decomposition:** Break down complex goals into small, manageable steps.
2.  **Efficient Action:** If multiple independent actions can be taken simultaneously to gather information, you MUST execute them in parallel as a single batch. This is more efficient than taking one step at a time.
3.  **Self-Correction:** If a tool fails or a user rejects an action, analyze the observation and create a new plan.

---
## 1. Context and History
Here is the information you have about the current situation.

**Current Working Directory:**
All file system operations are relative to this directory: `{current_working_directory}`

**Relevant Long-Term Memories (from past tasks):**
{memories_str}

**Current Task Conversation History:**
{history_str}

**User's Ultimate Goal:** "{initial_user_prompt}"

---
## 2. The Scratchpad: Your Step-by-Step Working Memory
The Scratchpad is the most important source of information for your decision-making. It contains the complete, step-by-step history of your actions and their observed outcomes for the current task. Your ability to achieve the user's goal depends on your ability to analyze this information.
Your Primary Task Here is Analysis:
    1. Before deciding your next action, you MUST critically analyze the Observation(s) from the last step recorded below.
    2. Review the Last Outcome: Carefully examine the result of your most recent action(s). Did they succeed? Did they fail? Did they return the data you expected?
    3. Extract Key Information: The observation is not just a log; it is data. It may contain file contents, lists of files from ls, command outputs, or error messages that you need to interpret.
Inform Your Next Step: You must use the information extracted from the scratchpad to formulate your next action(s). For example, if the last observation was a list of files, your next step might be to read several of them. The output of one step is often the required input for the next, but many steps can be independent.
This continuous loop of action -> observation -> analysis is how you make progress.

This is the scratchpad_str:
{scratchpad_str}

---
## 3. Your Task: Decide
Based on all the context above, you must now decide on the next set of actions. Follow this reasoning process carefully:

First, think step-by-step. Verbally reason through the following points in your mind. This is your internal monologue and is the MOST IMPORTANT part of your process.
   - **Recap:** What is the user's ultimate goal?
   - **Observation:** What were the results of my last batch of actions (from the scratchpad)? Are they what I expected?
   - **Analysis:** Based on the goal and the last observations, what are the next logical steps? Crucially, which of these steps are independent and can be run in parallel?
   - **Plan:** Formulate a plan for the next batch of actions. If I use these tools, what do I expect to happen? How does this get me closer to the user's goal?

**Decision:**
After your thought process, choose **ONE** of the two options below. Your entire output must be a single JSON object containing your chosen action (`tool_calls` or `final_answer`).

1. **`final_answer`**:
You will select `final_answer` ONLY under one of the following conditions:

    a) **SUCCESS:** You have executed all necessary steps, gathered all required information from your tools, and can now definitively and completely answer the user's original goal.
       - Example Thought: "I have successfully listed the files and read the content of 'config.yaml'. I have all the information needed to answer the user's question about the configuration."
       - Example JSON:
         ```json
         {{
           "final_answer": "I have listed the directory, and the content of 'main.py' is: [file content here]."
         }}
         ```

    b) **IRRECOVERABLE ERROR:** A previous tool call resulted in a critical error that prevents any further progress. This includes errors like "file not found," "directory not found," or "permission denied" when you cannot find an alternative path. You cannot continue, so you must stop and report.
       - Example Thought: "The user asked me to read 'api_keys.json', but the 'read_file' tool returned an error saying the file does not exist. I cannot proceed with the original plan without this file. I must stop and inform the user."
       - Example JSON:
         ```json
         {{
           "final_answer": "I'm sorry, I could not complete your request because the file 'api_keys.json' was not found in the current directory. Please check the file path or provide a new instruction."
         }}
         ```

    c) **TASK IMPOSSIBILITY:** After analyzing the user's request and your available tools, you conclude that the request is impossible to fulfill with your current capabilities.
       - Example Thought: "The user is asking me to 'open a web browser and log in to their email'. I do not have a tool to control a graphical web browser. This task is impossible for me."
       - Example JSON:
         ```json
         {{
           "final_answer": "I am unable to fulfill your request to 'open a web browser' as I can only operate through my available command-line and file system tools. Please provide a different task."
         }}
         ```

**IMPORTANT:** Do not choose `final_answer` if there are still logical, pending steps from the user's prompt that you have not yet attempted. Always prefer to use another tool if it could potentially lead to a solution. Exhaust all possible tool-based actions before concluding.

2.  **`tool_calls`**: If you need to perform one or more actions, provide a **list** of tool calls.

    **The Rule of Independence:** You can and SHOULD specify multiple tools in a list to be executed in parallel, BUT ONLY IF THEY ARE INDEPENDENT. An action is independent if it does not require the output from another action in the *same batch*.

    *   **GOOD EXAMPLE (Independent Actions):** The user wants to know what's in the `src` directory and also wants to read the `README.md` file. These can be done at the same time.
        ```json
        {{
          "tool_calls": [
            {{ "name": "list_directory", "parameters": {{ "path": "./src" }} }},
            {{ "name": "read_file", "parameters": {{ "file_path": "README.md" }} }}
          ]
        }}
        ```
    *   **BAD EXAMPLE (Dependent Actions):** You cannot create a file and write to it in the same batch, because the second action depends on the first one succeeding. These must be done in separate turns.
        ```json
        // INVALID - DO NOT DO THIS
        {{
          "tool_calls": [
            {{ "name": "run_shell_command", "parameters": {{ "command": "touch new_file.py" }} }},
            {{ "name": "write_file", "parameters": {{ "file_path": "new_file.py", "content": "# New file" }} }}
          ]
        }}
        ```

    **The Rule of Specificity:** Always Prefer a Specific Tool. Avoid using `run_shell_command` for actions that have a dedicated tool.
    *   To read a file's content: **CORRECT:** Use `read_file`. **INCORRECT:** Do not use `run_shell_command` with `cat`.
    *   To write or modify a file: **CORRECT:** Use `write_file`. **INCORRECT:** Do not use `run_shell_command` with `echo`.
    *   To list a directory's contents: **CORRECT:** Use `list_directory`. **INCORRECT:** Avoid `run_shell_command` with `ls` or `dir`.
    *   To produce information of a photo: **CORRECT**: Use `image_information`. **INCORRECT**: Do not use `run_shell_command`.
    *   Use `run_shell_command` only when no other tool can accomplish your goal (e.g., `cd`, `mkdir`, `mv`).

    YOU HAVE TO OUTPUT A JSON OBJECT EXACTLY AS PRESENTED IN THE TOOL SCHEMA: {tools_schema}
    """

def get_summarizer_system_prompt():
    return (
        "Analyze the provided technical output and identify the single most significant result, conclusion, or error. "
        "Your response MUST be only the summary itself, without any preamble or explanation. "
        "Limit the entire output to 1-2 sentences."
    )

def get_tool_summary_prompt(tool_name: str, tool_args: dict, tool_output: dict) -> str:
    prompt = f"""

Tool Name: {tool_name}
Arguments Used: {json.dumps(tool_args)}
Raw Output: {json.dumps(tool_output)}
"""
    if tool_name == "read_file":
        prompt = f"""
The `read_file` tool was just used. If the file content is short, you MUST include it. If it's long, you might just confirm it was read.

File Path: {tool_args.get('file_path')}
File Content Snippet: \"{tool_output.get('content', '')[:100]}...\""""
    elif tool_name == "write_file":
        prompt = f"""
The `write_file` tool was just used to write to a file. Please generate a concise confirmation message.

File Path: {tool_args.get('file_path')}
Result: {json.dumps(tool_output)}
"""
    elif tool_name == "list_directory":
        entries = tool_output.get('entries', [])
        #print(entries)
        prompt = f"""
The `list_directory` tool was just used. List ALL the contents of the directory for the user. DO NOT TRY TO SUMMARISE HERE. DO NOT SKIP ANY FOLDER/FILE IN THIS DIRECTORY.

Path: {tool_args.get('path')}
Entries: {', '.join(entries) if entries else 'None'}
"""
    elif tool_name == "run_shell_command":
        prompt = f"""
The `run_shell_command` tool was executed. Summarize the result for the user. Mention if there were any errors.

Command: {tool_args.get('command')}
Exit Code: {tool_output.get('exit_code')}
Output (stdout): {tool_output.get('stdout')}
Error (stderr): {tool_output.get('stderr')}
"""
    elif tool_name == "classify_folder":
        prompt = f"""
The `classify_folder` tool was used to classify all photos inside a folder based on a certain property.

Folder Path: {tool_args.get('folder_path')}
Property: {tool_args.get('property')}
Model Response: {tool_output.get('images_with_property', 'N/A')}
Error: {tool_output.get('error', 'N/A')}

List ONLY the photos that have the property. If there was an error, report it.
"""
    return prompt

def get_final_summary_system_prompt():
    """
    Returns a system prompt specifically for generating a final summary of a plan's execution.
    """
    return "You are a helpful assistant. Summarize the provided plan execution results in a concise, user-friendly text format. Focus on the overall outcome and any important details or errors. If no plan was executed, provide a general, helpful response based on the conversation. If the plan is read_file DO NOT summarise the contentsd of the file I want you to output the contents of the file as is. If the plan is list_directory include ALL directories do NOT summarise."
