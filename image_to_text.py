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

async def image_to_text_function(query: str,image_path: str) -> dict:

    image_url = f"http://172.17.0.1:{LOCAL_SERVER_PORT}/cli-ai-project/{image_path}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": f"Answer the query using the photo provided. Include all details might needed. The query is: {query}"}
                ]
            }
        ],
        "max_tokens": 200, 
        "temperature": 0.2
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

