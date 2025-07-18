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
    """Executes a SINGLE tool call. This function is now designed to be called concurrently."""
    global current_working_directory

    tool_name = tool_call.get('name')
    tool_args = tool_call.get('parameters')

    # This special handling for 'cd' should remain, as it modifies a global state.
    # Concurrent 'cd' calls would be problematic, but the LLM should be smart enough
    # not to propose multiple 'cd' calls in the same independent batch.
    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
        if command.strip().startswith("cd "):
            new_path = command.strip()[3:].strip()
            if os.path.isabs(new_path):
                target_path = new_path
            else:
                target_path = os.path.join(current_working_directory, new_path)
            
            target_path = os.path.normpath(target_path)

            if os.path.isdir(target_path):
                # Note: This is a side-effect that is not thread-safe by nature.
                # It's tolerated here because it's unlikely the LLM will issue
                # multiple 'cd' commands in a single parallel batch.
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
        
        # We print before execution for clarity, especially in a concurrent scenario.
        print(Fore.CYAN + f"Executing: {tool_name}({tool_args})")
        
        try:
            raw_output = await tool_function(**tool_args)
            summary = await summarize_tool_result(tool_name, tool_args, raw_output)
            print(Fore.GREEN + f"Result for {tool_name}: {summary}")
            return summary
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {e}"
            print(Fore.RED + error_msg)
            return error_msg
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
            print(decision)
            spinner.stop()

            # --- START: MODIFICATION FOR BATCH TOOL EXECUTION ---
            # The agent can now return a list of tool calls to be executed in parallel.
            if "tool_calls" in decision and decision["tool_calls"]:
                list_of_tool_calls = decision["tool_calls"]
                
                user_approved_batch = False
                
                if not task_confirmation_enabled:
                    user_approved_batch = True
                else:
                    # Formulate the question for the user, showing the full plan.
                    print(f"{Fore.YELLOW}The agent proposes the following parallel actions:")
                    for i, tool_call in enumerate(list_of_tool_calls):
                        tool_call = tool_call['function']
                        print(f"  {i+1}. {Fore.CYAN}{tool_call['name']}({tool_call['parameters']})")
                    
                    user_choice = input(f"{Fore.YELLOW}Proceed with this batch? (y/n/a - yes/no/always for this task): ").lower()

                    if user_choice in ['y', 'yes']:
                        user_approved_batch = True
                    elif user_choice in ['a', 'always']:
                        user_approved_batch = True
                        task_confirmation_enabled = False # Disable for the rest of this task
                        print(Fore.GREEN + "Confirmation disabled for the remainder of this task.")
                    else: # 'n', 'no', or anything else is a rejection
                        rejection_summary = "User rejected the proposed batch of actions."
                        print(Fore.RED + rejection_summary)
                        task_scratchpad.append(f"Observation: {rejection_summary}")
                        # We break here because the agent's plan was rejected. It needs to rethink.
                        # Depending on the desired behavior, you could also just continue to the next loop.
                        break

                if user_approved_batch:
                    # Create a list of concurrent tasks
                    tasks = [execute_tool_call(tc['function']) for tc in list_of_tool_calls]
                    
                    # Execute them all concurrently and wait for all to complete
                    print(Fore.YELLOW + f"--- Executing Batch of {len(tasks)} Actions ---")
                    batch_results = await asyncio.gather(*tasks)
                    print(Fore.YELLOW + f"--- Batch Execution Complete ---")

                    # Record the actions and their results in the scratchpad for the next LLM call
                    for tool_call, result_summary in zip(list_of_tool_calls, batch_results):
                        tool_call = tool_call['function']
                        task_scratchpad.append(f"Action: {tool_call['name']}({tool_call['parameters']})")
                        task_scratchpad.append(f"Observation: {result_summary}")

            # --- END: MODIFICATION FOR BATCH TOOL EXECUTION ---

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
                # This handles both the old "tool_call" format (if the LLM regresses) and any other invalid format.
                error_key = "tool_call" if "tool_call" in decision else "unknown format"
                error_msg = f"Error: Agent returned an invalid or outdated decision format ({error_key}). Expected 'tool_calls' or 'final_answer'."
                print(Fore.RED + error_msg)
                print(f"Decision received: {decision}")
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