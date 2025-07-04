
import asyncio
import aiofiles
import os
from typing import Optional

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
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "exit_code": process.returncode
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
                return {"content": content, "lines_read": len(sliced_lines)}
            else:
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

def list_directory(path: str = '.') -> dict:
    """Lists a directory and returns its contents as a list."""
    try:
        entries = os.listdir(path)
        return {"entries": entries}
    except Exception as e:
        return {"error": str(e)}

# --- 2. TOOL REGISTRY ---
available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
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
]
