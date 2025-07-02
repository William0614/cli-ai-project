import asyncio
import inspect
import threading
import itertools
import time
import sys
from ai_core import get_agent_decision, summarize_tool_result
from tools import available_tools
from memory import save_memory
from pathlib import Path
import os

memory_file = Path(os.getcwd()).resolve() / ".cli_ai" / "CLI_AI.md"
current_path = os.getcwd()

cur_conv = " "

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

async def execute_tool_call(tool_call: dict, current_path: str):
    # ... (this function remains the same)
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
    if tool_name in available_tools:
        tool_function = available_tools[tool_name]

        tool_args['file_path'] = current_path
        print(f"---\nExecuting: {tool_name}({tool_args})\n---")

        
        print(Fore.CYAN + f"Action: {tool_name}({tool_args})")
        

        if inspect.iscoroutinefunction(tool_function):
            raw_output = await tool_function(**tool_args)
        else:
            raw_output = tool_function(**tool_args)
        current_path = os.getcwd()
        summary = await summarize_tool_result(tool_name, tool_args, raw_output)
        print(Fore.GREEN + summary)
    else:
        print(Fore.RED + f"Error: Unknown tool '{tool_name}'.")

async def main():

    """The main async loop for the autonomous agent."""
    print(Fore.YELLOW + "Autonomous Agent Started. Type 'exit' to quit.")
    spinner = Spinner()
    global cur_conv
    cnt = 1
    while True:
        prompt = input("\nType your message > ")
        save_memory(f" User's prompt {cnt}: " + prompt + '\n')
        if not prompt:
            continue
        if prompt.lower() == "exit":
            with open(memory_file, "w", encoding="utf-8") as f:
                f.write(" ")  # This clears the file
            break
        save_memory(f"Your response {cnt}: ")
        cnt = cnt + 1
        current_path = os.getcwd()   
        spinner.start()
        decision = await get_agent_decision(prompt)
        # Stop the spinner immediately after the call returns
        spinner.stop()

        if "plan" in decision:
            # ... (rest of the logic remains the same)
            plan = decision["plan"]
            save_memory("The AI has proposed a plan:")
            print(Fore.YELLOW + "The AI has proposed a plan:")
            for i, step in enumerate(plan, 1):
                save_memory(f"  Step {i}: {step['name']}({step['arguments']})")
                print(Fore.YELLOW + f"  Step {i}: {step['name']}({step['arguments']})")
            
            approval = input("\nExecute this plan? (yes/no): ").lower()
            if approval == 'yes':
                print("Executing plan...")
                for step in plan:
                    await execute_tool_call(step)
                print(Fore.GREEN + "Plan execution finished.")
            else:
                save_memory("Plan aborted")
                print(Fore.RED + "Plan aborted.")

        elif "tool_call" in decision:
            await execute_tool_call(decision["tool_call"],current_path)

        elif "text" in decision:
            save_memory(f"AI: {decision['text']}")
            print(Fore.MAGENTA + f"AI: {decision['text']}")
            
        else:
            save_memory(f"Sorry, I received an unexpected decision format: {decision}")
            print(Fore.RED + f"Sorry, I received an unexpected decision format: {decision}")

        with open(memory_file,"r") as f:
            lines = f.readlines()
            end_index = 2
            for i, line in enumerate(lines):
                if line.strip().startswith("-  User's"):
                    end_index = i
                    break
                    i = i+1
            
            data = lines[2:end_index+1][::-1]
            data_str = ' '.join(data)
            tmp = data_str + cur_conv
            cur_conv = tmp
            print(cur_conv)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")