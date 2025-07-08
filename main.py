import asyncio
import inspect
import threading
import itertools
import time
import sys
import os
from ai_core import create_plan, summarize_plan_result
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

async def execute_tool(tool_name: str, tool_args: dict) -> dict:
    global current_working_directory

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
                return {"status": "Success", "output": f"Changed directory to {current_working_directory}"}
            else:
                return {"status": "Error", "output": f"Directory not found: {new_path}"}
        
        tool_args["directory"] = current_working_directory

    if tool_name in available_tools:
        tool_function = available_tools[tool_name]
        
        try:
            if inspect.iscoroutinefunction(tool_function):
                raw_output = await tool_function(**tool_args)
            else:
                raw_output = tool_function(**tool_args)
            return {"status": "Success", "output": raw_output}
        except Exception as e:
            return {"status": "Error", "output": f"Tool execution failed: {e}"}
    else:
        return {"status": "Error", "output": f"Unknown tool '{tool_name}'."}

async def main():
    print(Fore.YELLOW + "Autonomous Agent Started. Type '/voice' to toggle voice input. Type 'exit' to quit.")
    spinner = Spinner()
    history = []
    voice_input_enabled = False  # Voice input is off by default

    while True:
        user_input = ""
        if voice_input_enabled:
            print(Fore.CYAN + "\nListening for your command (voice enabled)...")
            user_input = get_voice_input_whisper(duration=5)
            if user_input:
                print(f"> You said: {user_input}")
            else:
                print(Fore.YELLOW + "No voice input detected, please use text input.")
                user_input = input("> ")
        else:
            print(Fore.CYAN + "\nPlease enter your command:")
            user_input = input("> ")

        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "/voice":
            voice_input_enabled = not voice_input_enabled
            status = "enabled" if voice_input_enabled else "disabled"
            print(Fore.GREEN + f"Voice input is now {status}.")
            continue


        history.append(f"User: {user_input}")

        spinner.start()
        decision = await create_plan(history, current_working_directory)
        spinner.stop()

        if "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"AI: {ai_response}")
            history.append(f"Agent: {ai_response}")

        elif "save_to_memory" in decision:
            fact_to_save = decision["save_to_memory"]
            memory.save_memory(fact_to_save, {"type": "declarative"})
            print(Fore.GREEN + f"Saved to memory: {fact_to_save}")

        elif "plan" in decision:
            plan = decision["plan"]
            plan_results = []
            
            print(Fore.YELLOW + "The AI has proposed a plan:")
            for i, step in enumerate(plan, 1):
                critical_tag = Fore.RED + "[CRITICAL]" if step.get("is_critical") else ""
                print(Fore.YELLOW + f"  Step {i}: {step['thought']} ({step['tool']}) {critical_tag}")

            approval = input("Execute this plan? (yes/no): ").lower()
            if approval != 'yes':
                print(Fore.RED + "Plan aborted by user.")
                history.append("Agent: Plan aborted by user.")
                continue

            step_outputs = []
            for i, step in enumerate(plan):
                print(Fore.CYAN + f"\n--- Executing Step {i+1}/{len(plan)} ---")
                print(Fore.CYAN + f"Thought: {step['thought']}")
                print(Fore.CYAN + f"Action: {step['tool']}({step['args']})")

                if step.get("is_critical"):
                    confirm = input(Fore.RED + "Confirm execution of this critical step? (yes/no): ").lower()
                    if confirm != 'yes':
                        print(Fore.RED + "Step aborted by user.")
                        plan_results.append({"tool": step['tool'], "status": "Aborted", "output": "User aborted critical step."})
                        break

                spinner.start()
                result = await execute_tool(step["tool"], step["args"])
                spinner.stop()

                step_outputs.append(result["output"])
                plan_results.append({"tool": step['tool'], "status": result["status"], "output": result["output"]})

                if result["status"] == "Error":
                    print(Fore.RED + f"Error in step {i+1}: {result['output']}")
                    break
                else:
                    print(Fore.GREEN + f"Step {i+1} completed successfully.")

                if "checkpoint" in step:
                    # This is a simplified checkpoint evaluation. A more robust version would use another LLM call.
                    if not result["output"] or "error" in str(result["output"]).lower() or "not found" in str(result["output"]).lower():
                        print(Fore.YELLOW + f"Checkpoint failed for step {i+1}: {step['checkpoint']}. Halting plan.")
                        break

            spinner.start()
            final_summary = await summarize_plan_result(plan_results)
            spinner.stop()

            print(Fore.MAGENTA + f"\nAI: {final_summary}")
            history.append(f"Agent: {final_summary}")

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