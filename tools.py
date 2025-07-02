import os
import glob
from pathlib import Path
from datetime import datetime
import asyncio
import aiofiles
import subprocess
from memory import save_memory

memory_file = Path(os.getcwd()).resolve() / ".cli_ai" / "CLI_AI.md"

async def run_shell_command(command: str, file_path: str) -> dict:
    """Executes a shell command and returns its output."""
    if command.strip().startswith("cd "):
        try:
            target_dir = command.strip()[3:].strip(" '\" ")
            new_path = os.path.abspath(os.path.join(file_path,target_dir))
            os.chdir(new_path)
            save_memory(f"Changed directory to: {new_path}")
            return {"directory": str(new_path)}
        except Exception as e:
            save_memory(f"Failed to change directory: {e}")
            return {"error": {e}}

    else:
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd = file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            save_memory(f"{stdout.decode()}")
            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode
            }
        except Exception as e:
            return {"error": str(e)}


async def read_file(file_path: str) -> dict:
    """Reads a file asynchronously and returns its content."""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return {"content": content}
    except Exception as e:
        save_memory(f"Error reading file: {e}")
        return {"error": str(e)}

async def write_file(file_path: str, content: str) -> dict:
    """Writes to a file asynchronously and returns a success status."""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return {"status": "success", "message": f"Successfully wrote to {file_path}"}
    except Exception as e:
        save_memory(f"Error writing to file: {e}")
        return {"error": str(e)}

def list_directory(file_path: str = '.') -> dict:
    """Lists a directory and returns its contents as a list."""
    try:
        entries = os.listdir(file_path)
        return {"entries": entries}
    except Exception as e:
        save_memory(f"Error listing directory: {e}")
        return {"error": str(e)}

available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
}


tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Executes a shell command.",
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
            "description": "Reads the content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "The path to the file."}
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
                    "file_path": {"type": "string", "description": "The directory path."}
                },
                "required": ["file_path"]
            }
        }
    }
]
