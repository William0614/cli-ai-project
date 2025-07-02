import os
import glob
from pathlib import Path
from datetime import datetime
import asyncio
import aiofiles
import subprocess



async def run_shell_command(command: str, file_path: str) -> str:
    """Executes a shell command and returns its output."""
    if command.strip().startswith("cd "):
        try:
            target_dir = command.strip()[3:].strip(" '\" ")
            new_path = os.path.abspath(os.path.join(file_path,target_dir))
            os.chdir(new_path)
            return f"Changed directory to: {new_path}"
        except Exception as e:
            return f"Failed to change directory: {e}"
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd = file_path,

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if stderr == b'':
            return f"\n{stdout.decode()}"
        elif stdout == b'':
            return f"\n{stderr.decode()}"
        else:
            return f"STDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}"

    except Exception as e:
        return f"Error executing command: {e}"

async def read_file(file_path: str) -> str:
    """Reads the content of a specified file."""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    except Exception as e:
        return f"Error reading file: {e}"

async def write_file(file_path: str, content: str) -> str:
    """Writes given content to a specified file."""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"

async def list_directory(file_path: str = '.') -> str:
    """Lists all the files and directories at a given path"""
    try:
        entries = os.listdir(file_path)
        return "\n".join(entries)
    except FileNotFoundError:
        return f"Error: Directory not found at {file_path}"
    except Exception as e:
        return f"Error listing directory: {e}"

async def find_files(pattern: str , file_path: str) -> dict[str]:
    """Searches for files matching some criteria based on the pattern in a specific directory sorted by modification date"""
    base_path = Path(file_path).resolve()
    search_pattern = str(base_path / pattern)

    matched_files = glob.glob(search_pattern, recursive = True)

    matched_files.sort(key=lambda f: os.path.getmtime(f), reverse = True)

    for file in matched_files:
        file.removeprefix(file_path)

    return matched_files

available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "find_files": find_files
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Executes a shell command and returns its output and errors.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file."
                    }
                },
                "required": ["command", "path"] 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a specified file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes given content to a specified file",
            "parameters": {
                "type": "object", 
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file we should write. We should add the text file to the current path."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content we want to write to the file."
                    }
                },
                "required": ["file_path", "content"] 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists all the files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Searches for files matching some criteria based on the pattern in a specific directory sorted by modification date.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The pattern that filters all the files based on the user's prompt"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file."
                    }
                },
                "required": ["pattern","file_path"] 
            }
        }
    }
    
]
