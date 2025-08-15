import asyncio
import json
import os
from ai_core import create_plan, summarize_plan_result
from executor import execute_plan
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
                if replan_count >= 1:
                    print(Fore.YELLOW + f"Replanning (replan attempt {replan_count + 1}/{MAX_REPLAN_ATTEMPTS + 1})...")
                plan_results, plan_halted = await execute_plan(current_plan, history)

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
                    
                    replan_approval = input("Try replan? (Enter/no): ").lower()
                    if replan_approval != '' and replan_approval != "yes":
                        break
                    
                    print(f"plan results: {plan_results}")
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
