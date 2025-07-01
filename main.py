import asyncio
import inspect # To check if a function is async
from ai_core import get_ai_response
from tools import available_tools

async def main():
    """The main async loop for the CLI agent."""
    print("Welcome to your Async AI-powered CLI. Type 'exit' to quit.")

    while True:
        prompt = input("Type your message > ")
        if prompt.lower() == "exit":
            print("Exiting...")
            break

        if not prompt:
            continue # Skip empty prompts

        # Get AI response asynchronously
        ai_response = await get_ai_response(prompt)

        if "tool_name" in ai_response:
            # If the AI response contains a tool call
            tool_name = ai_response["tool_name"]
            tool_args = ai_response["tool_args"]
            
            if tool_name in available_tools:
                # Get the tool function from the available tools
                tool_function = available_tools[tool_name]
                
                print(f"---\nExecuting: {tool_name}({tool_args})\n---")
                try:
                    # Check if the tool is async or regular
                    if inspect.iscoroutinefunction(tool_function):
                        result = await tool_function(**tool_args)
                    else:
                        result = tool_function(**tool_args)
                    print(f"Result:\n{result}")
                except Exception as e:
                    print(f"Error executing unknown tool '{tool_name}': {e}")
            
        elif "text" in ai_response:
            print(f"AI: {ai_response['text']}")

if __name__ == "__main__":
    # Start the asyncio event loop
    asyncio.run(main())