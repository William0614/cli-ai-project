import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import asyncio
import json
from ai_core import think, reflexion
from executor import execute_tool
from utils import Spinner
import memory_system as memory
from colorama import init, Fore

init(autoreset=True)

# --- Main Application Logic ---

current_working_directory = os.getcwd()

async def get_user_input(voice_input_enabled: bool) -> tuple[str, bool]:
    user_input = ""
    if voice_input_enabled:
        print(Fore.CYAN + "\nListening for your command (voice enabled)...")
        # user_input = get_voice_input_whisper(duration=5)
        if user_input:
            print(f"> You said: {user_input}")
        else:
            print(Fore.YELLOW + "No voice input detected, please use text input.")
            user_input = input("> ")
    else:
        print(Fore.CYAN + "Please enter your command:")
        user_input = input("> ")
    return user_input, voice_input_enabled


async def main():
    print(
        Fore.YELLOW
        + "Autonomous Agent Started. Type '/voice' to toggle voice input. Type 'exit' to quit."
    )
    spinner = Spinner("Thinking...")
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

        history.append({"role": "user", "content": user_input})

        spinner.start()
        decision = await think(history, current_working_directory)
        spinner.stop()

        if "text" in decision:
            ai_response = decision["text"]
            print(Fore.MAGENTA + f"Jarvis: {ai_response}")
            history.append({"role": "AI", "content": ai_response})
            continue

        elif "save_to_memory" in decision:
            fact_to_save = decision["save_to_memory"]
            memory.save_memory(fact_to_save, {"type": "declarative"})
            print(Fore.GREEN + f"Saved to memory: {fact_to_save}")
            history.append({"role": "AI", "content": f"Saved to memory: {fact_to_save}"})
            continue

        elif "action" in decision:
            action = decision["action"]
            current_goal = action.get("current_goal", "No specific goal provided for this action.") # Extract current_goal
            
            MAX_REPLANS = 3
            replan_count = 0
            
            while True:
                spinner.start()
                observation = await execute_tool(action["tool"], action["args"])
                spinner.stop()

                # Consolidated output
                output_block = f"""
{Fore.YELLOW}Thought: {action['thought']}
{Fore.BLUE}Current Goal: {current_goal}
{Fore.CYAN}Action: {action['tool']}({action['args']})
{Fore.GREEN}Observation: {observation}
"""
                print(output_block)
                history.append({"role": "AI", "content": {"thought": action['thought'], "current_goal": current_goal, "action": action['tool'], "args": action['args'], "observation": observation}})

                is_error = observation.get("status") == "Error"

                original_user_request = action.get("original_user_request", user_input) # Use the original user request if available
                # print(f"\nOriginal User Request: {original_user_request}")
                # print(f"\nObservation: {observation}")
                # print(f"\nFormatted observation: {json.dumps(observation, indent=2)}")
                # print(f"History: {json.dumps(history, indent=2)}")
                spinner.set_message("Reflecting on the result...")
                spinner.start()
                reflection = await reflexion(history, current_goal, original_user_request)
                spinner.set_message("Thinking...")
                spinner.stop()
                
                if reflection["decision"] == "finish":
                    print(Fore.MAGENTA + f"Jarvis: {reflection['comment']}")
                    history.append({'role': 'assistant', 'content': reflection['comment']})
                    break
                
                elif reflection["decision"] == "error":
                    print(Fore.RED + f"Reflexion decision == error. Error: {reflection['comment']}")
                    history.append({'role': 'assistant', 'content': f"Error: {reflection['comment']}"})
                    break

                elif reflection["decision"] == "continue":
                    if is_error:
                        replan_count += 1
                        if replan_count >= MAX_REPLANS:
                            print(Fore.RED + "Max replan attempts reached. Aborting task.")
                            history.append({'role': 'assistant', 'content': "Max replan attempts reached. Aborting task."})
                            break
                    
                    action = reflection["next_action"]
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            print(Fore.RED + error_msg)
            history.append({'role': 'assistant', 'content': f"Error: {error_msg}"})


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
    except KeyboardInterrupt or "exit":
        print("\nExiting...")
