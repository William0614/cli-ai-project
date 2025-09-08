import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import asyncio
import json
from datetime import datetime
from src.cli_ai.core.ai_engine import think_two_phase, reflexion, speak_text_openai, classify_intent
from src.cli_ai.tools.executor import execute_tool
from src.cli_ai.tools.audio.speech_to_text import get_voice_input_whisper
from src.cli_ai.utils.spinner import Spinner
from src.cli_ai.memory import SessionMemoryManager, VectorMemoryManager, UserInfoManager
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
        + "Autonomous Agent Started. Type '/voice' to toggle voice input, '/flush' to clear conversation, 'exit' to quit."
    )
    spinner = Spinner("Thinking...")
    
    # Initialize smart memory system
    session_memory = SessionMemoryManager(max_recent_length=20)  # Increased from 6 to 20 for tool execution
    vector_memory = VectorMemoryManager()
    user_info = UserInfoManager()
    print(Fore.GREEN + f"[Smart Memory] Session started: {session_memory.session_id}")
    print(Fore.GREEN + f"[Vector Memory] Connected to vector database")
    print(Fore.GREEN + f"[User Info] Automatic extraction enabled")
    
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
        if user_input.lower() == "/flush":
            # Extract user info from current session before flushing
            current_messages = session_memory.recent_messages.copy()
            if current_messages:
                extracted_info = await user_info.extract_user_info_from_conversation(current_messages)
                if extracted_info:
                    stored_count = user_info.store_user_info(extracted_info)
                    print(Fore.GREEN + f"[User Info] Extracted {stored_count} user information items before flush")
                
                print(Fore.BLUE + f"[Flush] Discarding {len(current_messages)} conversation messages")
            
            # Clear session memory
            session_memory.recent_messages.clear()
            session_memory.message_count = 0
            print(Fore.YELLOW + "[Session Flushed] Conversation history forgotten. User preferences preserved.")
            continue
        intent = await classify_intent(user_input)
        if intent == "exit_program" or user_input.lower() == "exit":
            # Extract user info and save session to vector storage before exit
            final_messages = session_memory.clear_session()
            if final_messages:
                # Extract user info from final session
                extracted_info = await user_info.extract_user_info_from_conversation(final_messages)
                if extracted_info:
                    stored_count = user_info.store_user_info(extracted_info)
                    print(Fore.GREEN + f"[User Info] Extracted {stored_count} user information items from session")
                
                # Store final conversations in vector database
                success = vector_memory.store_conversation_chunk(final_messages, {"reason": "session_end"})
                print(Fore.BLUE + f"[Smart Memory] Saving {len(final_messages)} messages to long-term storage")
                if success:
                    print(Fore.GREEN + f"[Vector Memory] Session conversations stored successfully")
                else:
                    print(Fore.RED + f"[Vector Memory] Error storing session conversations")
            await asyncio.sleep(1)
            break

        # Add user input to session memory (no overflow check yet)
        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now(),
            "message_id": session_memory.message_count,
            "session_id": session_memory.session_id,
            "metadata": {}
        }
        session_memory.recent_messages.append(user_message)
        session_memory.message_count += 1
        
        spinner.start()
        # Get recent messages for AI context (now includes retrieved memories from vector storage)
        history = session_memory.get_recent_messages_for_ai()
        # Use the new two-phase approach to reduce tool hallucinations
        decision = await think_two_phase(history, current_working_directory, voice_input_enabled, user_info, vector_memory)
        spinner.stop()

        if "text" in decision:
            ai_response = decision["text"]
            if voice_input_enabled:
                await speak_text_openai(ai_response)
            else:
                print(Fore.MAGENTA + f"Jarvis: {ai_response}")
            
            # Add AI response and check for overflow after complete exchange
            ai_message = {
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now(),
                "message_id": session_memory.message_count,
                "session_id": session_memory.session_id,
                "metadata": {}
            }
            session_memory.recent_messages.append(ai_message)
            session_memory.message_count += 1
            
            # Now check for overflow with complete user-assistant pair
            if len(session_memory.recent_messages) > session_memory.max_recent_length:
                overflow_count = len(session_memory.recent_messages) - session_memory.max_recent_length
                # Ensure we overflow in pairs
                if overflow_count % 2 != 0:
                    overflow_count += 1
                
                overflow_messages = session_memory.recent_messages[:overflow_count]
                session_memory.recent_messages = session_memory.recent_messages[overflow_count:]
                
                if overflow_messages:
                    # Extract user info before storing in vector database
                    extracted_info = await user_info.extract_user_info_from_conversation(overflow_messages)
                    if extracted_info:
                        stored_count = user_info.store_user_info(extracted_info)
                        print(Fore.GREEN + f"[User Info] Extracted {stored_count} user information items")
                    
                    # Store in vector database
                    success = vector_memory.store_conversation_chunk(overflow_messages, {"reason": "overflow", "trigger": "text_response"})
                    print(Fore.BLUE + f"[Smart Memory] {len(overflow_messages)} messages ({len(overflow_messages)//2} pairs) moved to long-term storage")
                    if success:
                        print(Fore.GREEN + f"[Vector Memory] Overflow stored in vector database")
                    else:
                        print(Fore.RED + f"[Vector Memory] Error storing overflow")
            continue

        elif "action" in decision:
            action = decision["action"]
            current_goal = action.get("current_goal", "No specific goal provided for this action.") # Extract current_goal
            
            # Enable tool execution mode to prevent memory overflow during tool use
            session_memory.set_tool_execution_mode(True)
            
            MAX_REPLANS = 5  # Increased from 3 to give more chances with better prompts
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

                # Add action to session memory using the optimized format
                # Note: For actions, we replace the user input with the complete action response
                # Remove the user input we added earlier and replace with complete exchange
                session_memory.recent_messages.pop()  # Remove the user input added earlier
                action_overflow = session_memory.add_action_response(
                    user_request=user_input,
                    thought=action['thought'],
                    action=action['tool'],
                    args=action['args'],
                    observation=observation,
                    metadata={"current_goal": current_goal, "action_type": "tool_execution"}
                )
                
                if action_overflow:
                    conversation_text = session_memory.format_conversation_for_storage(action_overflow)
                    print(Fore.BLUE + f"[Smart Memory] Action overflow: {len(action_overflow)} messages moved to storage")

                is_error = observation.get("status") == "Error"

                original_user_request = action.get("original_user_request", user_input) # Use the original user request if available
                spinner.stop()
                spinner.set_message("Reflecting on the result...")
                spinner.start()
                
                # Get current conversation history for reflexion
                current_history = session_memory.get_recent_messages_for_ai()
                reflection = await reflexion(current_history, current_goal, original_user_request, voice_input_enabled, vector_memory)
                spinner.stop()
                spinner.set_message("Thinking...")
                
                if reflection["decision"] == "finish":
                    # Disable tool execution mode when finishing
                    session_memory.set_tool_execution_mode(False)
                    
                    final_response = reflection["comment"]
                    if voice_input_enabled:
                        await speak_text_openai(final_response)
                    else:
                        print(Fore.MAGENTA + f"Jarvis: {final_response}")
                    
                    # Add final exchange to session memory
                    overflow = session_memory.add_exchange(user_input, final_response)
                    if overflow:
                        conversation_text = session_memory.format_conversation_for_storage(overflow)
                        print(Fore.BLUE + f"[Smart Memory] {len(overflow)} messages moved to long-term storage")
                    break
                
                elif reflection["decision"] == "error":
                    # Disable tool execution mode when erroring out
                    session_memory.set_tool_execution_mode(False)
                    
                    error_response = f"Error: {reflection['comment']}"
                    if voice_input_enabled:
                        await speak_text_openai(error_response)
                    else:
                        print(Fore.RED + f"Reflexion decision == error. {error_response}")
                    
                    # Add error exchange to session memory  
                    overflow = session_memory.add_exchange(user_input, error_response)
                    if overflow:
                        conversation_text = session_memory.format_conversation_for_storage(overflow)
                        print(Fore.BLUE + f"[Smart Memory] {len(overflow)} messages moved to long-term storage")
                    break

                elif reflection["decision"] == "continue":
                    if is_error:
                        replan_count += 1
                        if replan_count >= MAX_REPLANS:
                            # Disable tool execution mode when aborting due to max replans
                            session_memory.set_tool_execution_mode(False)
                            
                            abort_msg = f"Max replan attempts ({MAX_REPLANS}) reached. The AI seems stuck in a loop. This might be due to: 1) Tool parameter errors, 2) Insufficient tool capabilities, or 3) Memory context issues. Please try rephrasing your request or breaking it into smaller steps."
                            if voice_input_enabled:
                                await speak_text_openai(abort_msg)
                            else:
                                print(Fore.RED + abort_msg)
                            
                            # Add abort exchange to session memory
                            overflow = session_memory.add_exchange(user_input, abort_msg)
                            if overflow:
                                conversation_text = session_memory.format_conversation_for_storage(overflow)
                                print(Fore.BLUE + f"[Smart Memory] {len(overflow)} messages moved to long-term storage")
                            break
                    if voice_input_enabled:
                        await speak_text_openai(reflection["comment"])
                    else:
                        print(Fore.CYAN + reflection["comment"])
                    
                    # Update action and current_goal for the next iteration
                    action = reflection["next_action"]
                    # Update current_goal if provided in the next_action
                    if "current_goal" in action:
                        current_goal = action["current_goal"]
                        print(Fore.YELLOW + f"[Goal Updated] {current_goal}")
        else:
            error_msg = f"Sorry, I received an unexpected decision format: {decision}"
            if voice_input_enabled:
                await speak_text_openai(error_msg)
            else:
                print(Fore.RED + error_msg)
            
            # Add error exchange to session memory
            overflow = session_memory.add_exchange(user_input, f"Error: {error_msg}")
            if overflow:
                conversation_text = session_memory.format_conversation_for_storage(overflow)
                print(Fore.BLUE + f"[Smart Memory] {len(overflow)} messages moved to long-term storage")


if __name__ == "__main__":
    try:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "agent_memory.db"
        )
        if not os.path.exists(db_path):
            from src.cli_ai.utils.database import initialize_db

            initialize_db()
            print("Database initialized.")
        asyncio.run(main())
    except KeyboardInterrupt or "exit":
        print("\nExiting...")
