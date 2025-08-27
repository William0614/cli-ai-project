import asyncio
import inspect
import shlex
import json
import os
from colorama import Fore
from .tools import available_tools
from ..utils.spinner import Spinner

current_working_directory = os.getcwd()

async def execute_tool(tool_name: str, tool_args: dict) -> dict:
    global current_working_directory

    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
        if isinstance(command, str):
            if command.strip().startswith("cd "):
                new_path = command.strip()[3:].strip()
                parsed_path = shlex.split(new_path)
                new_path = parsed_path[0]
                if os.path.isabs(new_path):
                    target_path = new_path
                else:
                    target_path = os.path.join(current_working_directory, new_path)

                target_path = os.path.normpath(target_path)

                if os.path.isdir(target_path):
                    current_working_directory = target_path
                    return {
                        "tool name": tool_name,
                        "status": "Success",
                        "output": f"Changed directory to {current_working_directory}",
                    }
                else:
                    return {"tool name": tool_name, "status": "Error", "output": f"Directory not found: {new_path}"}
            tool_args["command"] = shlex.split(command)

        tool_args["directory"] = current_working_directory

    if tool_name in available_tools:
        tool_function = available_tools[tool_name]

        try:
            if inspect.iscoroutinefunction(tool_function):
                raw_output = await tool_function(**tool_args)
            else:
                raw_output = tool_function(**tool_args)
            if tool_name == "run_shell_command":
                if raw_output['result']['exit_code'] != 0:
                    return {"tool name": tool_name, "status": "Error", "output": raw_output}
            else: 
                if "error" in raw_output:
                    return {"tool name": tool_name, "status": "Error", "output": raw_output}
            return {"tool name": tool_name, "status": "Success", "output": raw_output}
        except Exception as e:
            return {"tool name": tool_name, "status": "Error", "output": f"Tool execution failed: {e}"}
    else:
        return {"tool name": tool_name, "status": "Error", "output": f"Unknown tool '{tool_name}'."}
