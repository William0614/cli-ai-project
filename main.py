
from ai_core import get_ai_response
# Import the dictionary that maps tool names to functions
from tools import available_tools

def main():
    """The main loop to run the CLI agent."""
    print("Welcome to your AI-powered CLI. Type 'exit' to quit.")

    while True:
        prompt = input("> ")
        if prompt.lower() == "exit":
            print("Exiting...")
            break

        # Get the structured response from the AI
        ai_response = get_ai_response(prompt)

        if "tool_name" in ai_response:
            # The AI wants to use a tool
            tool_name = ai_response["tool_name"]
            tool_args = ai_response["tool_args"]

            if tool_name in available_tools:
                # Find the correct function from our dictionary
                tool_function = available_tools[tool_name]
                
                print(f"---\nExecuting tool: {tool_name} with arguments: {tool_args}\n---")
                
                # Execute the function with the arguments provided by the AI
                try:
                    result = tool_function(**tool_args)
                    print(f"Result:\n{result}")
                except Exception as e:
                    print(f"Error executing tool {tool_name}: {e}")
            else:
                print(f"Error: The AI tried to use an unknown tool: {tool_name}")
        
        elif "text" in ai_response:
            # The AI just wants to talk
            print(f"Gemini: {ai_response['text']}")

if __name__ == "__main__":
    main()

