import os
import subprocess

def run_shell_command(command: str) -> str:
    """
    Executes a shell command and returns its output and errors.
    Args:
        command (str): The shell command to execute.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True  # This will raise an exception for non-zero exit codes
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {command}\nExit Code: {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def read_file(file_path: str) -> str:
    """
    Reads the content of a specified file.
    Args:
        file_path (str): The path to the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a specified file, overwriting it if it exists.
    Args:
        file_path (str): The path to the file.
        content (str): The content to write to the file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"

def list_directory(path: str = '.') -> str:
    """
    Lists the files and directories at a given path.
    Args:
        path (str): The directory path to list. Defaults to the current directory.
    """
    try:
        entries = os.listdir(path)
        return "\n".join(entries)
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except Exception as e:
        return f"Error listing directory: {e}"

# This dictionary maps tool names to the actual functions.
# It's crucial for executing the tool the AI chooses.
available_tools = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
}

