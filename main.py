import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import asyncio
import json
from ai_core import think, reflexion, speak_text_openai, classify_intent
from executor import execute_tool
from speech_to_text import get_voice_input_whisper
from utils import Spinner
import memory_system as memory
from colorama import init, Fore

init(autoreset=True)

# --- Main Application Logic ---

current_working_directory = os.getcwd()

async def get_user_input(voice_input_enabled: bool) -> tuple[str, bool]:
    user_input = ""
    if voice_input_enabled:
        user_input = get_voice_input_whisper()
        if user_input:
            print(f"> {user_input}")
            if user_input.lower() in ["stop voice input.", "disable voice input.", "switch to text input."]:
                voice_input_enabled = False
                print(Fore.GREEN + "Voice input is now disabled. Switching to text input.")
                return "", voice_input_enabled # Return empty string and updated flag
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
        if user_input.lower() == "/voice":
            voice_input_enabled = not voice_input_enabled
            if voice_input_enabled:
                await speak_text_openai("Voice input is now enabled.")
            else:
                print(Fore.GREEN + f"Voice input is now disabled.")
            continue
        intent = await classify_intent(user_input)
        if intent == "exit_program" or user_input.lower() == "exit":
            await asyncio.sleep(1)
            break
        history.append({"role": "user", "content": user_input})

        spinner.start()
        decision = await think(history, current_working_directory, voice_input_enabled)
        spinner.stop()

        if "text" in decision:
            ai_response = decision["text"]
            if voice_input_enabled:
                await speak_text_openai(ai_response)
            else:
                print(Fore.MAGENTA + f"Jarvis: {ai_response}")
            history.append({"role": "AI", "content": ai_response})
            continue

        elif "save_to_memory" in decision:
            fact_to_save = decision["save_to_memory"]
            memory.save_memory(fact_to_save, {"type": "declarative"})
            if voice_input_enabled:
                await speak_text_openai("Understood.")
            else:
                print(Fore.GREEN + f"Saved to memory: {fact_to_save}")
            history.append({"role": "AI", "content": f"Saved to memory: {fact_to_save}"})
            continue

        elif "action" in decision:
            action = decision["action"]
            current_goal = action.get("current_goal", "No specific goal provided for this action.") # Extract current_goal
            
            MAX_REPLANS = 3
            replan_count = 0
            
            while True:
                # Check if action is marked as critical and requires user confirmation
                if action.get("is_critical", False):
                    # print(f"Tool: {action['tool']}")
                    # print(f"Args: {action['args']}")
                    print(Fore.CYAN + f"Thought: {action['thought']}")
                    print(Fore.RED + "Critical Action")
                    while True:
                        response = input(Fore.YELLOW + "Do you want to proceed? (yes/no): ").strip().lower()
                        if response in ['yes', 'y']:
                            break
                        elif response in ['no', 'n']:
                            print("Operation cancelled by user.")
                            break
                        else:
                            print("Please answer 'yes' or 'no'")
                    
                    if response in ['no', 'n']:
                        break  # Exit the action loop
                
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
                if voice_input_enabled:
                    await speak_text_openai(action['thought'])
                else:
                    print(output_block)

                history.append({"role": "AI", "content": {"thought": action['thought'], "current_goal": current_goal, "action": action['tool'], "args": action['args'], "observation": observation}})

                is_error = observation.get("status") == "Error"

                original_user_request = action.get("original_user_request", user_input) # Use the original user request if available
                # print(f"\nOriginal User Request: {original_user_request}")
                # print(f"\nObservation: {observation}")
                # print(f"\nFormatted observation: {json.dumps(observation, indent=2)}")
                # print(f"History: {json.dumps(history, indent=2)}")
                spinner.stop()
                spinner.set_message("Reflecting on the result...")
                spinner.start()
                reflection = await reflexion(history, current_goal, original_user_request, voice_input_enabled)
                spinner.stop()
                spinner.set_message("Thinking...")
                
                if reflection["decision"] == "finish":
                    if voice_input_enabled:
                        await speak_text_openai(reflection["comment"])
                    else:
                        print(Fore.MAGENTA + f"Jarvis: {reflection['comment']}")
                    history.append({'role': 'assistant', 'content': reflection['comment']})
                    break
                
                elif reflection["decision"] == "error":
                    if voice_input_enabled:
                        await speak_text_openai(f"Error: {reflection['comment']}")
                    else:
                        print(Fore.RED + f"Reflexion decision == error. Error: {reflection['comment']}")
                    history.append({'role': 'assistant', 'content': f"Error: {reflection['comment']}"})
                    break

                elif reflection["decision"] == "continue":
                    if is_error:
                        replan_count += 1
                        if replan_count >= MAX_REPLANS:
                            if voice_input_enabled:
                                await speak_text_openai("Max replan attempts reached. Aborting task.")
                            else:
                                print(Fore.RED + "Max replan attempts reached. Aborting task.")
                            history.append({'role': 'assistant', 'content': "Max replan attempts reached. Aborting task."})
                            break
                    if voice_input_enabled:
                        await speak_text_openai(reflection["comment"])
                    else:
                        action = reflection["next_action"]
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            if voice_input_enabled:
                await speak_text_openai(error_msg)
            else:
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
