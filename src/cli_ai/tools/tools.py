
import asyncio
import aiofiles
import os
import inspect
from typing import Any, Optional
from .vision.image_classifier import describe_image
from .vision.similarity import find_similar_images

# --- 1. ASYNC TOOL IMPLEMENTATIONS ---

async def run_shell_command(command: list, directory: Optional[str] = None) -> dict:
    """Executes a shell command asynchronously and returns its structured output."""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
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

async def read_text_file(file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> dict:
    """
    Reads a text-based file asynchronously and returns its content, with optional line-based slicing.
    Only works with text files (.txt, .py, .js, .html, .css, .md, etc.). Cannot read binary files like PDFs, images, or executables.
    """
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
    except UnicodeDecodeError:
        return {"error": f"Cannot read file at {file_path}. This is not a text-based file."}
    except Exception as e:
        return {"error": str(e)}

async def write_file(file_path: str, content: str) -> dict:
    """Writes to a text-based file asynchronously and returns a success status."""
    if not isinstance(content, str):
        content = content['stdout']
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return {"result": "success"}
    except UnicodeDecodeError:
        return {"error": f"Cannot write file at {file_path}. This is not a text-based file."}
    except Exception as e:
        return {"error": str(e)}

def list_directory(path: str = '.') -> dict:
    """Lists a directory and returns its contents as a list."""
    try:
        entries = os.listdir(path)
        absolute_paths = [os.path.join(path, entry) for entry in entries]
        return {"result": absolute_paths}
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
    "read_text_file": read_text_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "describe_image": describe_image,
    "find_similar_images": find_similar_images
}

# --- TOOL DOCUMENTATION EXTRACTION ---
def get_tool_docstrings() -> str:
    """
    Extracts and formats docstrings from all available tools.
    This provides detailed implementation details to the LLM.
    """
    docstring_info = []
    
    for tool_name, tool_func in available_tools.items():
        try:
            # Get the function signature and docstring
            signature = inspect.signature(tool_func)
            docstring = inspect.getdoc(tool_func)
            
            if docstring:
                # Format the tool documentation
                tool_doc = f"""
=== {tool_name.upper()} ===
Function: {tool_name}{signature}
Documentation:
{docstring}
"""
                docstring_info.append(tool_doc)
        except Exception as e:
            # Fallback if inspection fails
            docstring_info.append(f"=== {tool_name.upper()} ===\nDocumentation unavailable: {e}")
    
    return "\n".join(docstring_info)

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
                    "command": {"type": "array", "items": {"type": "string"}, "description": "The command to execute, as a list of strings."},
                    "directory": {"type": "string", "description": "The directory to execute the command in. Defaults to the current working directory."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Reads the content of text-based files only (.txt, .py, .js, .html, .css, .md, .json, etc.). Cannot read binary files like PDFs, images, or executables. Use image-specific tools for image files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The absolute path to the TEXT file (never use for images, PDFs, or other binary files)."},
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
            "description": "Writes content to a text-basedfile.",
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
            "name": "describe_image",
            "description": "Analyzes and describes the content of image files (.jpg, .png, .webp, .avif, etc.). Can answer questions about what's in the image, identify objects, people, text, or analyze visual content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "The absolute path to the image file."},
                    "question": {"type": "string", "description": "The question to ask about the image, e.g., 'What is in this image?', 'Is there a dog?', 'Describe this photo'. Returns an 'is_match' boolean for yes/no questions."}
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
    {
        "type": "function", 
        "function": {
            "name": "find_similar_images",
            "description": "Finds images that look visually similar to a source image by comparing visual features. CRITICAL: Use EXACT parameter names as specified below - any deviation will cause errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string", 
                        "description": "The absolute path to the source image file."
                    },
                    "search_directory": {
                        "type": "string", 
                        "description": "The directory to search for similar images."
                    },
                    "top_k": {
                        "type": "integer", 
                        "description": "Number of similar images to return (default: 5)."
                    },
                    "threshold": {
                        "type": "float", 
                        "description": "Similarity threshold 0-1 (default: 0.5)."
                    }
                },
                "required": ["image_path", "search_directory"]
            }
        }
    }
]

