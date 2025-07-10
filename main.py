import asyncio
import os
import json
from ai_core import create_plan, gather_context
from executor import Executor
from speech_to_text import SpeechToText
from dotenv import load_dotenv

load_dotenv()

# Initialize SpeechToText (if needed)
stt = SpeechToText() if os.getenv("USE_SPEECH_RECOGNITION") == "True" else None

# Simple user confirmation function for critical actions
def user_confirm(message: str) -> bool:
    response = input(message).strip().lower()
    return response == 'yes'

async def main():
    history = []
    current_working_directory = os.getcwd()
    executor = Executor(user_confirm_callback=user_confirm)

    print("Welcome to the AI CLI. Type 'exit' to quit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        if stt:
            print("Listening...")
            user_input = stt.recognize_speech()
            print(f"You (Speech): {user_input}")
            if user_input.lower() == 'exit':
                break

        history.append(user_input)

        # Step 1: Understand and Deconstruct (Implicitly handled by the prompt and initial user input)
        print("\n--- Step 1: Understanding and Deconstructing Request ---")
        print(f"User Request: {user_input}")

        # Step 2: Gather Context (Plan Phase 1)
        gathered_context = await gather_context(user_input, current_working_directory)

        # Step 3: Formulate a Plan (Plan Phase 2)
        print("\n--- Step 3: Formulating a Plan ---")
        decision = await create_plan(history, current_working_directory, gathered_context)

        if "text" in decision:
            print(f"AI: {decision["text"]}")
        elif "save_to_memory" in decision:
            print(f"AI: I've noted that: {decision["save_to_memory"]}")
        elif "plan" in decision:
            plan = decision["plan"]
            print("AI: I have formulated a plan:")
            for i, step in enumerate(plan):
                print(f"  Step {i+1}: {step.get("thought", "No thought provided.")} (Tool: {step.get("tool")})")
            
            # Step 4: Execute
            print("\n--- Step 4: Executing Plan ---")
            plan_results = await executor.execute_plan(plan)

            # Step 5: Verify and Re-evaluate (and Summarize)
            print("\n--- Step 5: Verifying and Re-evaluating ---")
            # For now, we'll just summarize. In a real system, this would involve
            # running tests, linters, etc., and potentially re-planning.
            from ai_core import summarize_plan_result # Re-import if needed, or pass as arg
            summary = await summarize_plan_result(plan_results)
            print(f"AI (Summary): {summary}")
        else:
            print("AI: I could not understand the plan. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())