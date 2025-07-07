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
from speech_to_text import get_voice_input_whisper
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

current_working_directory = os.getcwd()

async def execute_tool_call(tool_call: dict) -> str:
    global current_working_directory

    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
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
    print(Fore.YELLOW + "Autonomous Agent Started. Say 'exit' to quit.")
    spinner = Spinner()
    history = []

    while True:
        print(Fore.CYAN + "\nListening for your command...")
        user_input = get_voice_input_whisper(duration=5)

        if user_input:
            print(f"> You said: {user_input}")
        else:
            print(Fore.YELLOW + "No voice input detected, please use text input.")
            user_input = input("> ")

        if not user_input:
            continue
        if user_input.lower() == "exit":
            break

        history.append(f"User: {user_input}")

        spinner.start()
        decision = await get_agent_decision(history, current_working_directory)
        spinner.stop()

        if "thought" in decision:
            print(Fore.BLUE + f"Thought: {decision['thought']}")

        if "save_to_memory" in decision:
            fact_to_save = decision["save_to_memory"]
            memory.save_memory(fact_to_save, {"type": "declarative"})
            print(Fore.GREEN + f"Saved to memory: {fact_to_save}")

        elif "plan" in decision:
            plan = decision["plan"]
            plan_results = []

            if len(plan) == 1:
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
                                break
                        else:
                            summary = await execute_tool_call(tool_call)
                            plan_results.append(f"Tool {tool_name} executed: {summary}")
                else:
                    print(Fore.RED + "Plan aborted by user.")
                    history.append("Agent: Plan aborted by user.")

            if plan_results:
                history.append(f"Agent: Plan Execution Results: {'; '.join(plan_results)}")
            
            spinner.start()
            final_decision = await get_agent_decision(history, current_working_directory, force_text_response=True)
            spinner.stop()

            if "text" in final_decision:
                ai_response = final_decision["text"]
                print(Fore.MAGENTA + f"AI: {ai_response}")
                history.append(f"Agent: {ai_response}")
            else:
                error_msg = f"Sorry, I received an unexpected final decision format: {final_decision}"
                print(Fore.RED + error_msg)
                history.append(f"Agent: Error: {error_msg}")

        elif "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"AI: {ai_response}")
            history.append(f"Agent: {ai_response}")
            
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            print(Fore.RED + error_msg)
            history.append(f"Agent: Error: {error_msg}")

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