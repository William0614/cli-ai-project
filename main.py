import asyncio
import inspect
import shlex
import threading
import itertools
import json
import time
import sys
import os
from ai_core import create_plan, summarize_plan_result
from tools import available_tools
import memory_system as memory
from speech_to_text import get_voice_input_whisper
from colorama import init, Fore

init(autoreset=True)


# --- The Loading Spinner Class ---
class Spinner:
    def __init__(self, message="Thinking..."):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.message = message
        self.running = False
        self.thread = None

    def _spin(self):
        while self.running:
            sys.stdout.write(f"\r{Fore.YELLOW}{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


# --- Main Application Logic ---

current_working_directory = os.getcwd()


async def execute_tool(tool_name: str, tool_args: dict) -> dict:
    global current_working_directory

    if tool_name == "run_shell_command":
        command = tool_args.get("command", "")
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
                    "status": "Success",
                    "output": f"Changed directory to {current_working_directory}",
                }
            else:
                return {"status": "Error", "output": f"Directory not found: {new_path}"}

        tool_args["directory"] = current_working_directory

    if tool_name in available_tools:
        tool_function = available_tools[tool_name]

        try:
            if inspect.iscoroutinefunction(tool_function):
                raw_output = await tool_function(**tool_args)
            else:
                raw_output = tool_function(**tool_args)
            if "error" in raw_output:
                return {"status": "Error", "output": raw_output["error"]}
            else:
                return {"status": "Success", "output": raw_output}
        except Exception as e:
            return {"status": "Error", "output": f"Tool execution failed: {e}"}
    else:
        return {"status": "Error", "output": f"Unknown tool '{tool_name}'."}


def substitute_placeholders(args: dict, step_outputs: list) -> dict:
    import re

    current_args = json.loads(json.dumps(args))  # Deep copy

    for arg_name, arg_value in list(current_args.items()):
        if isinstance(arg_value, str) and "<output_of_step_" in arg_value:
            # Find all placeholder expressions in the string
            # e.g., "<output_of_step_1>['result']" or "<output_of_step_2>.some_attribute"
            # This regex captures the full placeholder expression
            matches = re.findall(
                r"(<output_of_step_(\d+)>(\[.*?\]|\\.[\\w_]+)*)", arg_value
            )
            # print(f"matches: {matches}")
            for full_placeholder_str, step_num_str, _ in matches:
                step_num_to_get = int(step_num_str)
                # print(step_num_to_get)
                # print(f"step_outputs: {step_outputs}")
                if 0 < step_num_to_get <= len(step_outputs):
                    prev_output = step_outputs[step_num_to_get - 1]
                    # print(f"Prev_output: {prev_output}")
                    # Construct the Python expression to evaluate
                    # Replace the placeholder part with "prev_output"
                    python_expression = full_placeholder_str.replace(
                        f"<output_of_step_{step_num_str}>", "prev_output"
                    )

                    try:
                        evaluated_value = eval(
                            python_expression, {"prev_output": prev_output}
                        )
                        # print(f"evaluated_value: {evaluated_value}")
                        # Replace the original placeholder string with the evaluated value
                        # This handles cases like "photos/<output_of_step_1>['result']"
                        # print(f"full_placeholder_str: {full_placeholder_str}")
                        if isinstance(evaluated_value, dict) and 'result' in evaluated_value:
                            evaluated_value = evaluated_value['result']
                        
                        # If the placeholder is the entire string, replace it directly
                        # to preserve the type (e.g., list)
                        if full_placeholder_str == arg_value:
                            current_args[arg_name] = evaluated_value
                        else:
                            # Otherwise, handle string formatting for commands
                            if isinstance(evaluated_value, list):
                                # Join list items into a space-separated string for shell commands
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
                        # If eval fails, keep the original arg_value to avoid breaking the plan
                        current_args[arg_name] = arg_value
                else:
                    print(
                        f"Warning: Placeholder {full_placeholder_str} refers to an invalid step number."
                    )
    return current_args


async def get_user_input(voice_input_enabled: bool) -> tuple[str, bool]:
    user_input = ""
    if voice_input_enabled:
        print(Fore.CYAN + "\nListening for your command (voice enabled)...")
        user_input = get_voice_input_whisper(duration=5)
        if user_input:
            print(f"> You said: {user_input}")
        else:
            print(Fore.YELLOW + "No voice input detected, please use text input.")
            user_input = input("> ")
    else:
        print(Fore.CYAN + "Please enter your command:")
        user_input = input("> ")
    return user_input, voice_input_enabled


async def execute_plan(plan: list, spinner: Spinner, history: list) -> tuple[list, bool]:
    plan_results = []
    step_outputs = []
    plan_halted = False

    print(Fore.YELLOW + "The AI has proposed a plan:")
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
        return plan_results  # Return empty results if aborted

    for i, step in enumerate(plan):
        if plan_halted:
            break

        print(Fore.CYAN + f"\n--- Executing Step {i+1}/{len(plan)} ---")
        print(Fore.CYAN + f"Thought: {step['thought']}")

        current_args = substitute_placeholders(step["args"], step_outputs)

        # --- Tool Execution Logic (with expansion for specific tools) ---
        args_to_process = []
        is_expanded = False

        # Expand list arguments for shell commands to run them one by one
        if step['tool'] == 'run_shell_command' and 'command' in current_args:
            command_parts = current_args['command'].split()
            list_args = []
            for i, part in enumerate(command_parts):
                if isinstance(part, list):
                    list_args.append((i, part))
            
            if len(list_args) > 0:
                is_expanded = True
                # Currently handles one list argument per command
                arg_index, arg_list = list_args[0]
                for item in arg_list:
                    new_command_parts = command_parts.copy()
                    new_command_parts[arg_index] = item
                    new_args = current_args.copy()
                    new_args['command'] = " ".join(new_command_parts)
                    args_to_process.append(new_args)

        # Fallback for classify_image
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
                step_output_collector.append(result["output"])

        if plan_halted:
            continue

        # Consolidate output for the next step
        final_output = (
            step_output_collector[0]
            if len(step_output_collector) == 1
            else step_output_collector
        )

        step_outputs.append(final_output)
        plan_results.append(
            {"tool": step["tool"], "status": "Success", "output": final_output}
        )
        print(Fore.GREEN + f"Step {i+1} completed successfully.")

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
    return plan_results


async def main():
    print(
        Fore.YELLOW
        + "Autonomous Agent Started. Type '/voice' to toggle voice input. Type 'exit' to quit."
    )
    spinner = Spinner()
    history = []
    voice_input_enabled = False  # Voice input is off by default

    while True:
        user_input, voice_input_enabled = await get_user_input(voice_input_enabled)
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "/voice":
            voice_input_enabled = not voice_input_enabled
            status = "enabled" if voice_input_enabled else "disabled"
            print(Fore.GREEN + f"Voice input is now {status}.")
            continue

        history.append(f"User: {user_input}")

        spinner.start()
        decision = await create_plan(history, current_working_directory)
        spinner.stop()

        if "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"AI: {ai_response}")
            history.append(f"Agent: {ai_response}")

        elif "save_to_memory" in decision:
            fact_to_save = decision["save_to_memory"]
            memory.save_memory(fact_to_save, {"type": "declarative"})
            print(Fore.GREEN + f"Saved to memory: {fact_to_save}")

        elif "plan" in decision:
            current_plan = decision["plan"]
            MAX_REPLAN_ATTEMPTS = 2 # Define a limit for replanning attempts
            replan_count = 0

            while replan_count <= MAX_REPLAN_ATTEMPTS:
                print(Fore.YELLOW + f"Attempting plan (replan attempt {replan_count + 1}/{MAX_REPLAN_ATTEMPTS + 1})...")
                plan_results, plan_halted = await execute_plan(current_plan, spinner, history)

                if not plan_halted: # Plan executed successfully
                    print(Fore.GREEN + "Plan completed successfully.")
                    break # Exit replanning loop

                else: # Plan failed or was aborted
                    print(Fore.RED + "Plan execution failed or was aborted.")
                    replan_count += 1
                    if replan_count > MAX_REPLAN_ATTEMPTS:
                        print(Fore.RED + "Maximum replanning attempts reached. Aborting task.")
                        history.append("Agent: Failed to complete task after multiple replanning attempts.")
                        break # Exit replanning loop

                    # Add failure context to history for the Planner
                    failure_message = f"Agent: Previous plan failed. Results: {json.dumps(plan_results)}. Please generate a new plan to achieve the original goal, taking this failure into account."
                    history.append(failure_message)
                    print(Fore.YELLOW + "Attempting to replan...")

                    spinner.start()
                    replan_decision = await create_plan(history, current_working_directory)
                    spinner.stop()

                    if "plan" in replan_decision:
                        current_plan = replan_decision["plan"] # Use the new plan for the next attempt
                        print(Fore.YELLOW + "New plan generated. Retrying...")
                    elif "text" in replan_decision:
                        # LLM decided it can't replan or has a direct answer to the failure
                        ai_response = replan_decision["text"]
                        print(Fore.MAGENTA + f"AI: {ai_response}")
                        history.append(f"Agent: {ai_response}")
                        plan_halted = False # Treat as resolved by text response
                        break # Exit replanning loop
                    else:
                        print(Fore.RED + "Replanning failed to produce a valid plan or text response. Aborting.")
                        history.append("Agent: Replanning failed to produce a valid plan.")
                        break # Exit replanning loop

            # Summarize the final outcome (either success or max attempts reached)
            spinner.start()
            final_summary = await summarize_plan_result(plan_results) # Summarize the last attempt's results
            spinner.stop()

            print(Fore.MAGENTA + f"\nAI: {final_summary}")
            history.append(f"Agent: {final_summary}")

        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            print(Fore.RED + error_msg)
            history.append(f"Agent: Error: {error_msg}")


if __name__ == "__main__":
    try:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "agent_memory.db"
        )
        if not os.path.exists(db_path):
            from database import initialize_db

            initialize_db()
            print("Database initialized.")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
