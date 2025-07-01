import os
import asyncio
import aiofiles
import subprocess

async def run_shell_command(command: str) -> str:
    """Executes a shell command and returns its output."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
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
    
available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
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
                    }
                },
                "required": ["command"]
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
]
