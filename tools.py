
import asyncio
import aiofiles
import os
from typing import Any, Optional
from image_tools import classify_image

# --- 1. ASYNC TOOL IMPLEMENTATIONS ---

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
            "result": {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode
            }
        }
    except Exception as e:
        return {"error": str(e)}

async def read_file(file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> dict:
    """Reads a file asynchronously and returns its content, with optional line-based slicing."""
    if offset is not None and offset < 0:
        return {"error": "Offset must be a non-negative number."}
    if limit is not None and limit <= 0:
        return {"error": "Limit must be a positive number."}
    if offset is not None and limit is None:
        return {"error": "Limit must be provided when offset is used."}

    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            if offset is not None and limit is not None:
                lines = await f.readlines()
                sliced_lines = lines[offset : offset + limit]
                content = "".join(sliced_lines)
                return {"result": {"content": content, "lines_read": len(sliced_lines)}}
            else:
                content = await f.read()
                return {"result": {"content": content}}
    except FileNotFoundError:
        return {"error": f"File not found at {file_path}"}
    except Exception as e:
        return {"error": str(e)}

async def write_file(file_path: str, content: str) -> dict:
    """Writes to a file asynchronously and returns a success status."""
    if not isinstance(content, str):
        content = content['stdout']
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return {"result": "success"}
    except Exception as e:
        return {"error": str(e)}

def list_directory(path: str = '.') -> dict:
    """Lists a directory and returns its contents as a list."""
    try:
        entries = os.listdir(path)
        return {"result": entries}
    except Exception as e:
        return {"error": str(e)}

def select_from_list(data_list: list, index: Optional[int] = None, filter_key: Optional[str] = None, filter_value: Any = None, return_key: Optional[str] = None) -> dict:
    """Selects an item from a list by index or filters a list of dictionaries by key-value pair.

    Args:
        data_list (list): The list to select from or filter.
        index (Optional[int]): The 0-based index of the item to select.
        filter_key (Optional[str]): The key to filter dictionaries by.
        filter_value (Any): The value to match for the filter_key.
        return_key (Optional[str]): If provided, returns a list of values for this key from the filtered items.
    """
    if not isinstance(data_list, list):
        data_list = [data_list]
    try:
        if not isinstance(data_list, list):
            return {"error": "Input 'data_list' must be a list."}

        if index is not None and (filter_key is not None or filter_value is not None):
            return {"error": "Cannot use 'index' with 'filter_key' or 'filter_value' simultaneously."}

        if index is not None:
            if not (0 <= index < len(data_list)):
                return {"error": f"Index {index} is out of bounds for list of size {len(data_list)}."}
            return {"result": data_list[index]}
        elif filter_key is not None and filter_value is not None:
            filtered_list = [item for item in data_list if isinstance(item, dict) and item.get(filter_key) == filter_value]
            if return_key:
                return {"result": [item.get(return_key) for item in filtered_list if isinstance(item, dict)]}
            return {"result": filtered_list}
        else:
            return {"error": "Either 'index' or both 'filter_key' and 'filter_value' must be provided."}
    except Exception as e:
        return {"error": str(e)}

# --- 2. TOOL REGISTRY ---
available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "classify_image": classify_image,
    "select_from_list": select_from_list,
}

# --- 3. TOOL SCHEMA ---
tools_schema = [
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
                    "file_path": {"type": "string", "description": "The absolute path to the file."},
                    "offset": {"type": "integer", "description": "The 0-based line number to start reading from."},
                    "limit": {"type": "integer", "description": "The maximum number of lines to read."}
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
                    "file_path": {"type": "string", "description": "The path to the file."},
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
            "description": "Lists files and directories in a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The directory path."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "classify_image",
            "description": "Classifies an image or answers a question about its content using a local multimodal model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "The absolute path to the image file."},
                    "question": {"type": "string", "description": "The question to ask about the image, e.g., 'What is in this image?', 'Is there a dog?'. This tool will also return an 'is_match' boolean if the question is a yes/no type."}
                },
                "required": ["image_path", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_from_list",
            "description": "Selects an item from a list by its index or filters a list of dictionaries by a key-value pair.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_list": {"type": "array", "description": "The list to select from or filter."},
                    "index": {"type": "integer", "description": "The 0-based index of the item to select (mutually exclusive with filter_key/filter_value)."},
                    "filter_key": {"type": "string", "description": "The key to filter dictionaries by (requires filter_value)."},
                    "filter_value": {"type": "string", "description": "The value to match for the filter_key (requires filter_key)."},
                    "return_key": {"type": "string", "description": "If provided, returns a list of values for this key from the filtered items."}
                },
                "oneOf": [
                    {"required": ["data_list", "index"]},
                    {"required": ["data_list", "filter_key", "filter_value"]}
                ],
                "dependencies": {
                    "return_key": ["filter_key", "filter_value"]
                }
            }
        }
    },
]

