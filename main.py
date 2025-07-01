import asyncio
import inspect
from ai_core import *
from tools import available_tools
from memory import save_memory
from pathlib import Path
import os

memory_file = Path.home() / ".cli_ai" / "CLI_AI.md"


<<<<<<< HEAD
def main():
    """The main loop to run the CLI agent."""
    print("Welcome to your AI-powered CLI. Type 'exit' to quit.")
    # save_memory("Started the AI CLI agent.")
    while True:
        prompt_1 = "You are a Windows CLI agent. You can run shell commands, read and write files, and list directories. The current path is: " 
        
        with open(memory_file, 'r', encoding='utf-8') as file:
            prompt_2 = file.read()
        prompt_user = input("> ")
        # print(prompt_2)  
        current_path = os.getcwd()
        prompt =  prompt_1 + str(current_path) + '\n' + prompt_user
        if prompt_user.lower() == "exit":
=======
async def execute_tool_call(tool_call: dict):
    """Executes a single tool call."""
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("arguments", {})
    
    if tool_name in available_tools:
        tool_function = available_tools[tool_name]
        print(f"---\nExecuting: {tool_name}({tool_args})\n---")
        if inspect.iscoroutinefunction(tool_function):
            result = await tool_function(**tool_args)
        else:
            result = tool_function(**tool_args)
        print(f"Result:\n{result}")
    else:
        print(f"Error: Unknown tool '{tool_name}'.")

async def main():
    """The main async loop for the autonomous agent."""
    print("Autonomous Agent Started. Type 'exit' to quit.")

    while True:
        prompt = input("\nType your message > ")
        if not prompt:
            continue # Skip empty inputs
        if prompt.lower() == "exit":
>>>>>>> 47f535602828e83362a18987ab732af083dbc8aa
            print("Exiting...")
            with open(memory_file, "w", encoding="utf-8") as f:
                f.write(" ")  # This clears the file
            break

<<<<<<< HEAD
        # Get the structured response from the AI
        ai_response = get_ai_response(prompt)

        save_memory(f"User: {prompt_user}")

        print(f"AI Response: {ai_response}")

        if "tool_name" in ai_response:
            # The AI wants to use a tool
            tool_name = ai_response["tool_name"]
            tool_args = ai_response["tool_args"]

            if tool_name in available_tools:
                # Find the correct function from our dictionary
                tool_function = available_tools[tool_name]
                #tool_args.setdefault("path", current_path)
                
                print(f"---\nExecuting tool: {tool_name} with arguments: {tool_args}\n---")
                
                # Execute the function with the arguments provided by the AI
                try:
                    # For file operations and directory listing, we need to ensure the current path is set correctly
                    #tool_args['path'] = os.getcwd() if 'path' not in tool_args else tool_args['path']
                    result = tool_function(**tool_args)
                    current_path = os.getcwd()
                    print(f"Result:\n{result}")
                except Exception as e:
                    print(f"Error executing tool {tool_name}: {e}")
            else:
                print(f"Error: The AI tried to use an unknown tool: {tool_name}")
        
        elif "text" in ai_response:
            # The AI just wants to talk
            print(f"Gemini: {ai_response['text']}")
            save_memory(f"Gemini: {ai_response['text']}")
            save_memory("\n\n")
=======
        # Get the AI's decision on how to proceed
        decision = await get_ai_decision(prompt)

        if "plan" in decision:
            # --- The AI decided to create a plan ---
            plan = decision["plan"]
            print("The AI has created a plan:")
            for i, step in enumerate(plan, 1):
                print(f"  Step {i}: {step['name']}({step['arguments']})")
            
            approval = input("\nShould I execute this plan? (yes/no): ").lower()
            if approval == 'yes':
                print("Executing plan...")
                for step in plan:
                    await execute_tool_call(step)
                print("Plan execution finished.")
            else:
                print("Plan aborted.")
>>>>>>> 47f535602828e83362a18987ab732af083dbc8aa

        elif "tool_call" in decision:
            await execute_tool_call(decision["tool_call"])

        elif "text" in decision:
            print(f"AI: {decision['text']}")
            
        else:
            print(f"Sorry, I received an unexpected decision format: {decision}")

if __name__ == "__main__":
    asyncio.run(main())
