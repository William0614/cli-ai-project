import asyncio
import inspect
import shlex
import json
import os
from colorama import Fore
from tools import available_tools
from utils import Spinner

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
            print(f"raw_output: {raw_output}")
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

def substitute_placeholders(args: dict, step_outputs: list) -> dict:
    import re

    current_args = json.loads(json.dumps(args))  # Deep copy

    for arg_name, arg_value in list(current_args.items()):
        if isinstance(arg_value, str) and "<output_of_step_" in arg_value:
            matches = re.findall(
                r"(<output_of_step_(\d+)>(\[.*?\]|\\.[\\w_]+)*)", arg_value
            )
            for full_placeholder_str, step_num_str, _ in matches:
                step_num_to_get = int(step_num_str)
                if 0 < step_num_to_get <= len(step_outputs):
                    prev_output = step_outputs[step_num_to_get - 1]
                    python_expression = full_placeholder_str.replace(
                        f"<output_of_step_{step_num_str}>", "prev_output"
                    )

                    try:
                        evaluated_value = eval(
                            python_expression, {"prev_output": prev_output}
                        )
                        if isinstance(evaluated_value, dict) and 'result' in evaluated_value:
                            evaluated_value = evaluated_value['result']
                        
                        if full_placeholder_str == arg_value:
                            current_args[arg_name] = evaluated_value
                        else:
                            if isinstance(evaluated_value, list):
                                replacement_str = ' '.join(f'"{item}"' for item in evaluated_value)
                            else:
                                replacement_str = str(evaluated_value)
                            
                            current_args[arg_name] = arg_value.replace(
                                full_placeholder_str, replacement_str
                            )
                    except Exception as e:
                        print(
                            f"Warning: Could not evaluate placeholder expression '{python_expression}': {e}"
                        )
                        current_args[arg_name] = arg_value
                else:
                    print(
                        f"Warning: Placeholder {full_placeholder_str} refers to an invalid step number."
                    )
    return current_args


async def execute_plan(plan: list, history: list) -> tuple[list, bool]:
    plan_results = []
    step_outputs = []
    plan_halted = False

    print(Fore.YELLOW + "The AI has proposed a plan:")
    if "overall_thought" in plan:
        print(Fore.CYAN + f"Overall Thought: {plan['overall_thought']}")
    for i, step in enumerate(plan, 1):
        critical_tag = Fore.RED + "[CRITICAL]" if step.get("is_critical") else ""
        print(
            Fore.YELLOW
            + f"  Step {i}: {step['thought']} ({step['tool']}) {critical_tag}"
        )

    approval = input("Execute this plan? (Enter/no): ").lower()
    if not (approval == "" or approval == "yes"):
        print(Fore.RED + "Plan aborted by user.")
        history.append("Agent: Plan aborted by user.")
        return plan_results, True

    for i, step in enumerate(plan):
        if plan_halted:
            break

        print(Fore.CYAN + f"\n--- Executing Step {i+1}/{len(plan)} ---")

        current_args = substitute_placeholders(step["args"], step_outputs)

        args_to_process = []
        is_expanded = False

        if step['tool'] == 'run_shell_command' and 'command' in current_args:
            command_parts = current_args['command'].split()
            list_args = []
            for c, part in enumerate(command_parts):
                if isinstance(part, list):
                    list_args.append((c, part))
            
            if len(list_args) > 0:
                is_expanded = True
                arg_index, arg_list = list_args[0]
                for item in arg_list:
                    new_command_parts = command_parts.copy()
                    new_command_parts[arg_index] = item
                    new_args = current_args.copy()
                    new_args['command'] = " ".join(new_command_parts)
                    args_to_process.append(new_args)

        elif step['tool'] == 'classify_image' and 'image_path' in current_args:
            if isinstance(current_args['image_path'], list):
                is_expanded = True
                for item in current_args['image_path']:
                    new_args = current_args.copy()
                    new_args['image_path'] = item
                    args_to_process.append(new_args)

        if not is_expanded:
            args_to_process.append(current_args)

        step_output_collector = []
        for single_args in args_to_process:
            print(Fore.CYAN + f"Action: {step['tool']}({single_args})")

            if step.get("is_critical"):
                confirm = input(
                    Fore.RED + "Confirm execution of this critical step? (Enter/no): "
                ).lower()
                if not (confirm == "" or confirm == "yes"):
                    print(Fore.RED + "Step aborted by user.")
                    plan_results.append(
                        {
                            "tool": step["tool"],
                            "status": "Aborted",
                            "output": "User aborted critical step.",
                        }
                    )
                    plan_halted = True
                    break
            
            spinner = Spinner("Executing...")
            spinner.start()
            result = await execute_tool(step["tool"], single_args)
            spinner.stop()
            if result["status"] == "Error":
                print(Fore.RED + f"Error in step {i+1}: {result['output']}")
                plan_results.append(
                    {
                        "tool": step["tool"],
                        "status": "Error",
                        "output": result["output"],
                    }
                )
                plan_halted = True
                break
            else:
                print(f"{result}\n")
                step_output_collector.append(result["output"])

        if plan_halted:
            continue

        final_output = (
            step_output_collector[0]
            if len(step_output_collector) == 1
            else step_output_collector
        )

        step_outputs.append(final_output)
        plan_results.append(
            {"tool": step["tool"], "status": "Success", "output": final_output}
        )
        print(Fore.GREEN + f"{final_output}")

        if "checkpoint" in step:
            if (
                not final_output
                or "error" in str(final_output).lower()
                or "not found" in str(final_output).lower()
            ):
                print(
                    Fore.YELLOW
                    + f"Checkpoint failed for step {i+1}: {step['checkpoint']}. Halting plan."
                )
                break
    return plan_results, plan_halted
