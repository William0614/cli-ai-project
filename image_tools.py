import requests
import json
import time
import os
from pathlib import Path
import http.server
import socketserver
import threading
from typing import Optional, Dict, Any

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
        httpd = socketserver.TCPServer(("", LOCAL_SERVER_PORT), Handler)
        
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        server_running = True
        print(f"Local image server started on port {LOCAL_SERVER_PORT}")
    except Exception as e:
        print(f"Error starting local image server: {e}")
        server_running = False

async def classify_image(image_path: str, property: str) -> dict:

    start_local_server_if_not_running()

    if not os.path.exists(image_path):
        return {"error": f"Folder not found at {image_path}"}

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
                    {"type": "text", "text": "ONLY output 0 or 1. If the image has the following property output 1, otherwise output 0: " + property}
                ]
            }
        ],
        "max_tokens": 1, 
        "temperature": 0.0
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        return {"response": content.strip()}
    except requests.exceptions.RequestException as e:
        return {"error": f"API Error for {image_url}: {e}"}
    except (KeyError, IndexError) as e:
        return {"error": f"Could not parse response for {image_url}: {e}. Full response: {response_data}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

async def classify_folder(folder_path: str, property: str) -> dict:
    """
    Classifies all images in a folder based on a given property.

    Args:
        folder_path: The absolute or relative path to the folder containing images.
        property: The property to check for in the images (e.g., "contains a dog").

    Returns:
        A dictionary containing lists of images that have the property,
        do not have the property, and any errors encountered during classification.
    """
    if not os.path.isdir(folder_path):
        return {"error": f"Folder not found at path: {folder_path}"}

    # FIX 1: Initialize results locally as a dictionary.
    results = {
        "images_with_property": [],
        "images_without_property": [],
        "errors": []
    }

    # Define common image file extensions to filter for
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    # FIX 3: Ensure the local image server is running before making requests.
    start_local_server_if_not_running()

    print(f"Scanning folder '{folder_path}' for property: '{property}'...")

    image_files = [f for f in os.listdir(folder_path) if any(f.lower().endswith(ext) for ext in image_extensions)]

    for filename in image_files:
        image_path = os.path.join(folder_path, filename)
        
        classification_result = await classify_image(image_path, property)

        # FIX 2: Handle all possible outcomes from the classification.
        if "error" in classification_result:
            results["errors"].append({
                "image": image_path,
                "reason": classification_result["error"]
            })
        elif classification_result.get("response") == "1":
            results["images_with_property"].append(image_path)
        elif classification_result.get("response") == "0":
            results["images_without_property"].append(image_path)
        else:
            # Catch any other unexpected (but not error) responses
            results["errors"].append({
                "image": image_path,
                "reason": f"Unexpected response from API: {classification_result}"
            })

    return results
