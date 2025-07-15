
import asyncio
import aiofiles
import os
from typing import Optional
import asyncio
import aiofiles
import os
from image_tools import classify_folder
from pathlib import Path
from web_search import search_and_screenshot
from image_to_text import image_to_text_function
import time

# --- 1. ASYNC TOOL IMPLEMENTATIONS ---

from datetime import datetime

def get_current_date_and_time():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    return current_date

def relative_path() -> str:
    from main import current_working_directory
    current_path = current_working_directory
    root = Path(os.getcwd()).resolve()
    current = Path(current_path).resolve()
    relative_path = current.relative_to(root)

    return str(relative_path)


async def run_shell_command(command: str, directory: Optional[str] = None) -> dict:
    """Executes a shell command asynchronously and returns its structured output."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=directory # Use the provided directory
        )
        stdout, stderr = await process.communicate()
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "exit_code": process.returncode
        }
    except Exception as e:
        return {"error": str(e)}

async def read_file(file_path: str) -> dict:
    """Reads a file asynchronously and returns its content, with optional line-based slicing."""
    file_path_upd = Path.cwd() / relative_path() / file_path
    print(file_path_upd)
    try:
        async with aiofiles.open(file_path_upd, 'r', encoding='utf-8') as f:
                content = await f.read()
                return {"content": content}
    except FileNotFoundError:
        return {"error": f"File not found at {file_path}"}
    except Exception as e:
        return {"error": str(e)}

async def write_file(file_path: str, content: str) -> dict:
    """Writes to a file asynchronously and returns a success status."""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return {"status": "success", "message": f"Successfully wrote to {file_path}"}
    except Exception as e:
        return {"error": str(e)}

async def list_directory(path: str = '.') -> dict:
    """Lists a directory and returns its contents as a list."""
    try:
        entries = os.listdir(relative_path()+'/'+ path)
        return {"entries": entries}
    except Exception as e:
        return {"error": str(e)}

async def image_information(query: str, file_path) -> dict:
    try:
        answer = await image_to_text_function(query,file_path)
        return answer
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

async def tell_weather(query: str) -> dict:

    real_query = query + ' ' + "weather bbc"
    await search_and_screenshot(real_query)
    answer = await image_to_text_function(real_query+". Tell the weather taking into consideration that the current date is " +  get_current_date_and_time(), "screenshot.png")
    try:
        result = answer["response"]
        return {"response": result}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


# --- 2. TOOL REGISTRY ---
available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "image_information": image_information,
    "tell_weather": tell_weather
}

# --- 3. TOOL SCHEMA ---
tools_schema = [
{
    "tool_calls":[
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Executes a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to execute."},
                    "directory": {"type": "string", "description": "The directory to execute the command in. Defaults to the current working directory."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a file, optionally from a specific line offset and for a certain number of lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the file."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the file."},
                    "content": {"type": "string", "description": "The content to write."}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists ALL files and directories in a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The RELATIVE directory path. YOUR CURRENT PATH IS THE Current Working Directory."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "image_information",
            "description": "Answers the query about the image and gain information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A clear and concise question about the image"},
                    "file_path": {"type": "string", "description": "The RELATIVE path of the image."}
                },
                "required": ["query","file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tell_weather",
            "description": "Tells the weather in specific time and place",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The place and time the user wants to know the weather in one string"}
                },
                "required": ["query"]
            }
        }
    }
    ]
}
]

