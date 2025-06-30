
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Import the function definitions from tools.py
# This is how the model knows what functions it can call.
from tools import run_shell_command, read_file, write_file, list_directory

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create a generative model that knows about our tools
# We pass the actual function objects to the model.
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[run_shell_command, read_file, write_file, list_directory]
)

def get_ai_response(prompt: str) -> dict:
    """
    Gets a response from the Gemini model, which may be a function call or a text response.
    Returns a dictionary containing the tool call information or a text response.
    """
    try:
        # Start a chat session to maintain context
        chat = model.start_chat()
        response = chat.send_message(prompt)

        # Check if the model wants to call a tool
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            tool_name = function_call.name
            tool_args = {key: value for key, value in function_call.args.items()}
            return {
                "tool_name": tool_name,
                "tool_args": tool_args
            }
        else:
            # If no tool is called, return the text response
            return {
                "text": response.text
            }

    except Exception as e:
        print(f"Error communicating with Gemini API: {e}")
        return {"text": "An error occurred."}
