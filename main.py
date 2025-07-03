import asyncio
import inspect
import threading
import itertools
import time
import sys
import os # Import os module
from ai_core import get_agent_decision, summarize_tool_result
from tools import available_tools # Keep available_tools for execute_tool_call
from memory import save_memory, recall_memory # Import memory functions directly
from colorama import init, Fore

init(autoreset=True)

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
        # Clear the line after stopping
        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# --- Main Application Logic ---

# Global variable to track the current working directory
current_working_directory = os.getcwd() # Initialize with the actual current working directory

async def execute_tool_call(tool_call: dict) -> str:
    global current_working_directory # Declare global to modify it

    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
        # Update current_working_directory if a 'cd' command is executed
        if command.strip().startswith("cd "):
            new_path = command.strip()[3:].strip()
            # Handle absolute and relative paths
            if os.path.isabs(new_path):
                target_path = new_path
            else:
                target_path = os.path.join(current_working_directory, new_path)
            
            # Normalize path (e.g., resolve '..' and '.')
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
        
        # For other shell commands, execute in the current_working_directory
        # The run_shell_command tool itself will use this argument
        tool_args["directory"] = current_working_directory 

    if tool_name in available_tools:
        tool_function = available_tools[tool_name]
        
        print(Fore.CYAN + f"Action: {tool_name}({tool_args})")
        
        if inspect.iscoroutinefunction(tool_function):
            raw_output = await tool_function(**tool_args)
        else:
            raw_output = tool_function(**tool_args)
        
        summary = await summarize_tool_result(tool_name, tool_args, raw_output)
        print(Fore.GREEN + summary)
        return summary
    else:
        error_msg = f"Error: Unknown tool '{tool_name}'."
        print(Fore.RED + error_msg)
        return error_msg

async def main():
    print(Fore.YELLOW + "Autonomous Agent Started. Type 'exit' to quit.")
    spinner = Spinner()

    while True:
        user_input = input("\n> ")
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break

        # Save user input to memory as a conversation turn
        save_memory(f"User: {user_input}", memory_type="conversation")

        # Construct history for the agent: recent conversation + relevant saved facts
        conversation_history = recall_memory(memory_type="conversation", limit=10).get("facts", []) # Last 10 conversation turns
        relevant_facts = recall_memory(query=user_input, memory_type="fact").get("facts", []) # Only relevant saved facts
        history_for_agent = conversation_history + relevant_facts

        # Add current working directory to the history for the agent's context
        # This is now handled by passing it as a separate argument to get_agent_decision

        # Start the spinner right before the async call
        spinner.start()
        decision = await get_agent_decision(history_for_agent, current_working_directory) # Pass current_working_directory
        # Stop the spinner immediately after the call returns
        spinner.stop()

        if "thought" in decision:
            print(Fore.BLUE + f"Thought: {decision['thought']}")

        if "plan" in decision:
            plan = decision["plan"]
            plan_results = []

            if len(plan) == 1:
                # Single step plan: execute directly without showing plan or asking overall approval
                tool_call = plan[0]
                tool_name = tool_call.get("name")
                is_critical = tool_call.get("is_critical", False)

                if is_critical:
                    individual_approval = input(Fore.RED + f"Confirm execution of critical action '{tool_name}({tool_call.get('arguments', {})})'? (yes/no):").lower()
                    if individual_approval == 'yes':
                        summary = await execute_tool_call(tool_call)
                        plan_results.append(f"Tool {tool_name} executed: {summary}")
                    else:
                        print(Fore.RED + "Action aborted by user.")
                        plan_results.append(f"Tool {tool_name} aborted by user.")
                else:
                    summary = await execute_tool_call(tool_call)
                    plan_results.append(f"Tool {tool_name} executed: {summary}")

            else:
                # Multi-step plan: show plan and ask for overall approval
                print(Fore.YELLOW + "The AI has proposed a plan:")
                for i, step in enumerate(plan, 1):
                    tool_name = step.get("name")
                    tool_args = step.get("arguments", {})
                    is_critical = step.get("is_critical", False)
                    critical_tag = Fore.RED + "[CRITICAL]" if is_critical else ""
                    print(Fore.YELLOW + f"  Step {i}: {tool_name}({tool_args}) {critical_tag}")
                
                overall_approval = input("Execute this plan? (yes/no):").lower()
                if overall_approval == 'yes':
                    for tool_call in plan:
                        tool_name = tool_call.get("name")
                        is_critical = tool_call.get("is_critical", False)

                        if is_critical:
                            individual_approval = input(Fore.RED + f"Confirm execution of critical action '{tool_name}({tool_call.get('arguments', {})})'? (yes/no):").lower()
                            if individual_approval == 'yes':
                                summary = await execute_tool_call(tool_call)
                                plan_results.append(f"Tool {tool_name} executed: {summary}")
                            else:
                                print(Fore.RED + "Action aborted by user.")
                                plan_results.append(f"Tool {tool_name} aborted by user.")
                                break # Abort the rest of the plan
                        else:
                            summary = await execute_tool_call(tool_call)
                            plan_results.append(f"Tool {tool_name} executed: {summary}")
                else:
                    print(Fore.RED + "Plan aborted by user.")
                    save_memory("Plan aborted by user.", memory_type="conversation") # Save to memory

            # After executing the plan (or single step), feed the results back to the agent for a final response
            if plan_results: # Only append if something was executed
                save_memory(f"Plan Execution Results: {'; '.join(plan_results)}", memory_type="conversation") # Save to memory
            
            # Get a final text response from the agent based on the plan's outcome
            spinner.start()
            # Recall memory again to include plan execution results for final decision
            recalled_memory_for_final = recall_memory(memory_type="conversation", limit=10).get("facts", []) + recall_memory(query=user_input, memory_type="fact").get("facts", []) # Pass user_input for relevance
            final_decision = await get_agent_decision(recalled_memory_for_final, current_working_directory, force_text_response=True) # Pass current_working_directory
            spinner.stop()

            if "text" in final_decision:
                ai_response = final_decision["text"]
                print(Fore.MAGENTA + f"AI: {ai_response}")
                save_memory(f"AI: {ai_response}", memory_type="conversation") # Save to memory
            else:
                error_msg = f"Sorry, I received an unexpected final decision format: {final_decision}"
                print(Fore.RED + error_msg)
                save_memory(f"Error: {error_msg}", memory_type="conversation") # Save to memory

        elif "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"AI: {ai_response}")
            save_memory(f"AI: {ai_response}", memory_type="conversation") # Save to memory
            
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            print(Fore.RED + error_msg)
            save_memory(f"Error: {error_msg}", memory_type="conversation") # Save to memory

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")