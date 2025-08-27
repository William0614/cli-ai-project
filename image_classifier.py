"""
Enhanced image classification with OpenAI API support.
This extends the existing image_tools.py functionality.
"""
import os
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
USE_OPENAI = os.getenv("USE_OPENAI_VISION", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug: Print configuration (remove this after testing)
print(f"DEBUG: USE_OPENAI_VISION = {os.getenv('USE_OPENAI_VISION')}")
print(f"DEBUG: USE_OPENAI = {USE_OPENAI}")
print(f"DEBUG: OPENAI_API_KEY exists = {bool(OPENAI_API_KEY)}")
print(f"DEBUG: OPENAI_API_KEY starts with = {OPENAI_API_KEY[:10] if OPENAI_API_KEY else 'None'}...")

# Import the original function
from image_tools import classify_image as local_classify_image

def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 for OpenAI API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """Get MIME type from file extension."""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg', 
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')

async def describe_image_openai(image_path: str, question: str) -> Dict[str, Any]:
    """Describe and analyze image using OpenAI Vision API."""
    if not OPENAI_API_KEY:
        return {"error": "OpenAI API key not found in environment variables", "image_path": image_path}
    
    try:
        # Use context manager so the async HTTP client is closed inside the same event loop
        base64_image = encode_image_base64(image_path)
        mime_type = get_image_mime_type(image_path)

        async with AsyncOpenAI(api_key=OPENAI_API_KEY) as client:
            response = await client.chat.completions.create(
                model="gpt-4o",  # Options: gpt-4o-mini, gpt-4o, gpt-4-turbo
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.0,
                response_format={"type": "text"}
            )

            # Response handling: normalize to string safely
            raw = None
            try:
                raw = response.choices[0].message.content
            except Exception:
                # Fallback for other response shapes
                raw = str(response)

            content = (raw or "").strip()
            # keep original casing for description, but determine yes/no for is_match
            is_match = content.lower().startswith('yes')

            return {
                "response": content,
                "image_path": image_path,
                "is_match": is_match
            }
        
    except Exception as e:
        return {
            "error": f"OpenAI API Error: {e}",
            "image_path": image_path
        }

def describe_image(image_path: str, question: str) -> Dict[str, Any]:
    """
    Describe and analyze an image - automatically chooses between local and OpenAI based on configuration.
    
    To use OpenAI instead of local model:
    1. Set environment variable: USE_OPENAI_VISION=true
    2. Set environment variable: OPENAI_API_KEY=your_key_here
    """
    if USE_OPENAI:
        # Use a simpler approach - run in new thread to avoid event loop issues
        import asyncio
        import threading
        
        result = None
        exception = None
        
        def run_async():
            nonlocal result, exception
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(describe_image_openai(image_path, question))
                loop.close()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()
        
        if exception:
            return {"error": f"OpenAI API Error: {exception}", "image_path": image_path}
        return result
    else:
        # Use the original local implementation
        return local_classify_image(image_path, question)

# For direct async usage
async def describe_image_async(image_path: str, question: str) -> Dict[str, Any]:
    """Async version that chooses between local and OpenAI."""
    if USE_OPENAI:
        return await describe_image_openai(image_path, question)
    else:
        # Wrap the sync local function
        return await asyncio.to_thread(local_classify_image, image_path, question)
