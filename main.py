

import asyncio
import inspect
import threading
import itertools
import time
import sys
from ai_core import get_agent_decision, summarize_tool_result
from tools import available_tools
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

async def execute_tool_call(tool_call: dict) -> str:
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
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
    history = []

    while True:
        user_input = input("\n> ")
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break

        history.append(f"User: {user_input}")

        # Start the spinner right before the async call
        spinner.start()
        decision = await get_agent_decision(history)
        # Stop the spinner immediately after the call returns
        spinner.stop()

        if "tool_call" in decision:
            summary = await execute_tool_call(decision["tool_call"])
            history.append(f"Tool Output: {summary}")

        elif "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"AI: {ai_response}")
            history.append(f"AI: {ai_response}")
            
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            print(Fore.RED + error_msg)
            history.append(f"Error: {error_msg}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
