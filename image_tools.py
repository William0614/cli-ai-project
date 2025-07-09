import requests
import json
import time
import os
from pathlib import Path
import http.server
import socketserver
import threading
from typing import Optional
from openai import AsyncOpenAI

# Create an async client pointing to your local server
client = AsyncOpenAI(
    base_url="http://localhost:8002/v1",
    api_key="not-needed"
)

# --- Configuration ---
API_URL = "http://localhost:8002/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"
LOCAL_SERVER_PORT = 8887

# Global variables for server management
server_thread: Optional[threading.Thread] = None
httpd: Optional[socketserver.TCPServer] = None
server_running: bool = True

class LocalImageServer(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve files from the current working directory
        # This is a simplification; in a real scenario, you might want to restrict this
        # to a specific 'photos' directory or similar.
        super().do_GET()

def start_local_server_if_not_running():
    global server_thread, httpd, server_running

    if server_running:
        return

    try:
        # Set up the server to serve from the current working directory
        # This allows the model to access images from anywhere the agent is working
        Handler = LocalImageServer
        httpd = socketserver.TCPServer( ( "", LOCAL_SERVER_PORT), Handler)
        
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        server_running = True
        print(f"Local image server started on port {LOCAL_SERVER_PORT}")
    except Exception as e:
        print(f"Error starting local image server: {e}")
        server_running = False

async def parse_boolean_response(text_response: str, boolean_question: str) -> Optional[bool]:
    """Uses an LLM to parse a text response into a boolean (True/False/None for ambiguous)."""
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that parses text into a boolean. Respond with only 'true', 'false', or 'ambiguous'."},
                {"role": "user", "content": f"Given the text: \"{text_response}\". Does it answer \"{boolean_question}\"? Respond with 'true', 'false', or 'ambiguous'."}
            ],
            max_tokens=10,
            temperature=0.0
        )
        parsed_content = response.choices[0].message.content.strip().lower()
        if parsed_content == "true":
            return True
        elif parsed_content == "false":
            return False
        else:
            return None # Ambiguous
    except Exception as e:
        print(f"Error parsing boolean response: {e}")
        return None

async def is_boolean_question(question: str) -> bool:
    """Uses an LLM to determine if a question is a boolean (yes/no) type."""
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies questions. Respond with only 'true' if the question is a boolean (yes/no) question, otherwise 'false'."},
                {"role": "user", "content": f"Is the following a boolean question: \"{question}\"?"}
            ],
            max_tokens=10,
            temperature=0.0
        )
        parsed_content = response.choices[0].message.content.strip().lower()
        return parsed_content == "true"
    except Exception as e:
        print(f"Error determining boolean question: {e}")
        return False

async def classify_image(image_path: str, question: str) -> dict:
    """Classifies an image using the Qwen model via a local server.

    Args:
        image_path (str): The absolute path to the image file.
        question (str): The question to ask the model about the image.

    Returns:
        dict: A dictionary containing the model's response or an error message.
    """
    start_local_server_if_not_running()

    if not os.path.exists(image_path):
        return {"error": f"Image file not found at {image_path}"}

    # Construct the URL for the image relative to the server's root
    # Assuming the server serves from the current working directory
    # We need to make the path relative to the CWD for the server to find it
    try:
        relative_image_path = os.path.relpath(image_path, os.getcwd())
    except ValueError:
        # If image_path is on a different drive on Windows, relpath might fail
        # In such cases, we might need a more sophisticated server or a different approach
        return {"error": f"Image path {image_path} is not relative to the current working directory. Cannot serve."}

    image_url = f"http://172.17.0.1:{LOCAL_SERVER_PORT}/cli-ai-project/{relative_image_path}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": question}
                ]
            }
        ],
        "max_tokens": 100, # Allow for more descriptive answers
        "temperature": 0.0
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        
        result = {"response": content.strip(), "image_path": image_path}

        # If the question implies a yes/no answer, try to parse it into a boolean
        if await is_boolean_question(question):
            is_match = await parse_boolean_response(content, question)
            if is_match is not None:
                result["is_match"] = is_match

        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"API Error for {image_url}: {e}", "image_path": image_path}
    except (KeyError, IndexError) as e:
        return {"error": f"Could not parse response for {image_url}: {e}. Full response: {response_data}", "image_path": image_path}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}", "image_path": image_path}