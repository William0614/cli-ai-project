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
        super().do_GET()

def start_local_server_if_not_running():
    global server_thread, httpd, server_running

    if server_running:
        return

    try:
        Handler = LocalImageServer
        httpd = socketserver.TCPServer( ( "", LOCAL_SERVER_PORT), Handler)
        
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        server_running = True
        print(f"Local image server started on port {LOCAL_SERVER_PORT}")
    except Exception as e:
        print(f"Error starting local image server: {e}")
        server_running = False

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
    try:
        relative_image_path = os.path.relpath(image_path, os.getcwd())
    except ValueError:
        return {"error": f"Image path {image_path} is not relative to the current working directory. Cannot serve."}

    image_url = f"http://172.17.0.1:{LOCAL_SERVER_PORT}/multimodal-cli-agent/{relative_image_path}"

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
        "max_tokens": 100,
        "temperature": 0.0
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        content = response_data['choices'][0]['message']['content'].strip().lower()
        
        # Simplified boolean check
        is_match = content.startswith('yes')

        result = {
            "response": content, 
            "image_path": image_path,
            "is_match": is_match
        }

        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"API Error for {image_url}: {e}", "image_path": image_path}
    except (KeyError, IndexError) as e:
        return {"error": f"Could not parse response for {image_url}: {e}. Full response: {response_data}", "image_path": image_path}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}", "image_path": image_path}