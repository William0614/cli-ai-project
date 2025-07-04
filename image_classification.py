import requests
import json
import time
from pathlib import Path

# For serving local files, which is necessary for the API
import http.server
import socketserver
import threading

# --- Configuration ---
# The API endpoint for the chat completions
API_URL = "http://localhost:8002/v1/chat/completions"

# The model you want to use
MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"

# The folder containing the images to classify
IMAGE_FOLDER = "photos"

# The port for our temporary local web server
LOCAL_SERVER_PORT = 8888

# --- Main Classification Logic ---
def get_yes_no_answer(image_url, prompt_text):
    """Sends a request to the model and expects a 'yes' or 'no' answer."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are an image analysis assistant. You must answer the user's question about the image with only the word 'yes' or 'no'."
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt_text}
                ]
            }
        ],
        "max_tokens": 5,
        "temperature": 0.0
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        return content.strip().lower().replace('.', '')
    except requests.exceptions.RequestException as e:
        print(f"  -> API Error for {image_url}: {e}")
        return "error"
    except (KeyError, IndexError) as e:
        print(f"  -> Could not parse response for {image_url}: {e}")
        print("  -> Full Response:", response_data)
        return "error"


# --- Main Execution ---
if __name__ == "__main__":
    # --- Get the classification prompt from the user ---
    print("--- Yes/No Image Classifier ---")
    user_question = input("Enter a yes/no question to classify images by (e.g., 'Is there a dog in this photo?'): ")
    
    if not user_question.strip():
        print("Error: Prompt cannot be empty.")
        exit()

    # The base path where images are located
    base_path = Path(IMAGE_FOLDER)
    
    # Initialize the dictionary to store the results
    results = {
        "matching_files": [],
        "non_matching_files": [],
        "error_files": []
    }

    
    # --- Start Classification ---
    print(f"\n--- Starting Classification in '{IMAGE_FOLDER}' Folder ---")
    print(f"Criteria: '{user_question}'")

    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    image_files = [p for p in base_path.iterdir() if p.is_file() and p.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"No images found in the '{IMAGE_FOLDER}' directory.")

    for image_path in image_files:
        print(f"Processing '{image_path.name}'...")

        image_url = f"http://localhost:{LOCAL_SERVER_PORT}/{image_path.as_posix()}"
        
        answer = get_yes_no_answer(image_url, user_question)
        
        print(f"  -> Model answered: '{answer}'")
        
        # Get the full, unambiguous path of the file
        absolute_path_str = str(image_path.resolve())

        # Add the file path to the appropriate list in the results dictionary
        if answer == "yes":
            results["matching_files"].append(absolute_path_str)
            print(f"  -> Added to 'matching_files' list.")
        elif answer == "error":
            results["error_files"].append(absolute_path_str)
            print(f"  -> Added to 'error_files' list.")
        else: # This covers 'no' and any other unexpected response
            results["non_matching_files"].append(absolute_path_str)
            print(f"  -> Added to 'non_matching_files' list.")
            

        
    # --- Print the final results ---
    print("\n--- Final Results ---")
    print(json.dumps(results, indent=2))