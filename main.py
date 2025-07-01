import asyncio
import inspect
from ai_core import *
from tools import available_tools

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
            print("Exiting...")
            break

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

        elif "tool_call" in decision:
            await execute_tool_call(decision["tool_call"])

        elif "text" in decision:
            print(f"AI: {decision['text']}")
            
        else:
            print(f"Sorry, I received an unexpected decision format: {decision}")

if __name__ == "__main__":
    asyncio.run(main())
