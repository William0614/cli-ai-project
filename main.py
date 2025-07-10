import asyncio
import inspect
import threading
import itertools
import time
import sys
import os
from ai_core import get_agent_decision, summarize_tool_result
from tools import available_tools
import memory_system as memory
from colorama import init, Fore

init(autoreset=True)

# --- START: New Configuration Setting ---
# Set to True to require user confirmation before each tool call.
CONFIRMATION_REQUIRED_BY_DEFAULT = True
# --- END: New Configuration Setting ---

# --- The Loading Spinner Class ---
class Spinner:
    def __init__(self, message="Thinking..."):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.message = message
        self.running = False
        self.thread = None

    def _spin(self):
        while self.running:
            sys.stdout.write(f"\r{Fore.YELLOW}{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear the line when stopping
        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.flush()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()

# --- Main Application Logic ---
global current_working_directory
current_working_directory = os.getcwd()

def get_directory() -> str:
    return current_working_directory

async def execute_tool_call(tool_call: dict) -> str:
    global current_working_directory

    tool_name = tool_call["name"]
    tool_args = tool_call["parameters"]

    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
        # This logic correctly handles the 'cd' command within the tool execution.
        if command.strip().startswith("cd "):
            new_path = command.strip()[3:].strip()
            if os.path.isabs(new_path):
                target_path = new_path
            else:
                target_path = os.path.join(current_working_directory, new_path)
            
            target_path = os.path.normpath(target_path)

            if os.path.isdir(target_path):
                current_working_directory = target_path
                summary = f"Changed directory to {current_working_directory}"
                print(Fore.GREEN + summary)
                return summary
            else:
                summary = f"Error: Directory not found: {new_path}"
                print(Fore.RED + summary)
                return summary
        
        tool_args["directory"] = current_working_directory

    if tool_name in available_tools:
        tool_function = available_tools[tool_name]
        
        # The print statement is now part of the confirmation prompt,
        # but we can keep one here for when confirmation is disabled.
        print(Fore.CYAN + f"Executing: {tool_name}({tool_args})")
        
   
        raw_output = await tool_function(**tool_args)
        summary = await summarize_tool_result(tool_name, tool_args, raw_output)
        print(Fore.GREEN + summary)
        return summary
    else:
        error_msg = f"Error: Unknown tool '{tool_name}'."
        print(Fore.RED + error_msg)
        return error_msg

async def main():
    print(Fore.YELLOW + "Adaptive Autonomous Agent Started. Type 'exit' to quit.")
    spinner = Spinner()
    conversation_history = []
    max_steps_per_task = 10 

    while True:
  
        initial_user_prompt = input(f"\n{Fore.GREEN}> ")
        if not initial_user_prompt:
            continue
        if initial_user_prompt.lower() == "exit":
            break

        conversation_history.append(f"User: {initial_user_prompt}")

        # --- MODIFIED: Reset confirmation for each new task ---
        task_confirmation_enabled = CONFIRMATION_REQUIRED_BY_DEFAULT
        task_scratchpad = []
        task_in_progress = True
        step_counter = 0

        while task_in_progress and step_counter < max_steps_per_task:

            step_counter += 1
            spinner.start()
            decision = await get_agent_decision(
                conversation_history,
                initial_user_prompt,
                task_scratchpad, 
                current_working_directory
            )
            spinner.stop()

            # --- START: Major Change - Confirmation Logic ---
            if "tool_call" in decision:
                tool_call = decision["tool_call"]
                
                user_approved_action = False
                action_summary = ""

                if not task_confirmation_enabled:
                    user_approved_action = True
                else:
                    # Formulate the question for the user
                    tool_name = tool_call["name"]
                    tool_args = tool_call["parameters"]
                    prompt_message = f"Proposed Action: {Fore.CYAN}{tool_name}({tool_args})"
                    
                    user_choice = input(f"{prompt_message}\n{Fore.YELLOW}Proceed? (y/n/a - yes/no/always for this task): ").lower()

                    if user_choice in ['y', 'yes']:
                        user_approved_action = True
                    elif user_choice in ['a', 'always']:
                        user_approved_action = True
                        task_confirmation_enabled = False # Disable confirmation for the rest of this task
                        print(Fore.GREEN + "Confirmation disabled for the remainder of this task.")
                    else: # 'n', 'no', or anything else is a rejection
                        action_summary = "User rejected the proposed action."
                        print(Fore.RED + action_summary)
                        user_approved_action = False

                # Execute the action only if approved
                if user_approved_action:
                    action_summary = await execute_tool_call(tool_call)
                else:
                    break
                # Record the action and its result (either success, failure, or user rejection)
                task_scratchpad.append(f"Action: {tool_call['name']}({tool_call['parameters']})")
                task_scratchpad.append(f"Observation: {action_summary}")
            # --- END: Major Change - Confirmation Logic ---

            elif "final_answer" in decision:
                ai_response = decision["final_answer"]
                print(Fore.MAGENTA + f"AI: {ai_response}")
                
                task_in_progress = False
                conversation_history.append(f"Agent: {ai_response}")
                
                if task_scratchpad:
                    memory_entry = (
                        f"On the task '{initial_user_prompt}', I took these steps:\n"
                        + "\n".join(task_scratchpad)
                        + f"\nAnd concluded with: {ai_response}"
                    )
                    memory.save_memory(memory_entry, {"type": "procedural_summary"})
                    print(Fore.GREEN + "Saved task summary to long-term memory.")

            else:
                error_msg = f"Error: Agent returned an invalid decision format: {decision}"
                print(Fore.RED + error_msg)
                conversation_history.append(f"Agent: Error: {error_msg}")
                task_in_progress = False

        if step_counter >= max_steps_per_task:
            error_msg = "Error: Maximum steps reached for this task. Aborting."
            print(Fore.RED + error_msg)
            conversation_history.append(f"Agent: {error_msg}")


if __name__ == "__main__":
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_memory.db')
        if not os.path.exists(db_path):
            from database import initialize_db
            initialize_db()
            print("Database initialized.")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")