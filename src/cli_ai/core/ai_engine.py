import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .prompts import get_react_system_prompt, get_reflexion_prompt, get_final_summary_prompt, get_reflexion_prompt_with_tools
from ..utils.os_helpers import get_os_info
import soundfile as sf
import sounddevice as sd
import io

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

load_dotenv()

DEBUG_PROMPTS = os.getenv("DEBUG_PROMPTS", "false").lower() == "true"
openai_api_key = os.getenv("OPENAI_API_KEY")

client = None

def get_client():
    """Get or create the OpenAI client."""
    global client
    if client is None:
        client = AsyncOpenAI(api_key=openai_api_key)
    return client

def count_tokens(text: str, model: str = "gpt-5-nano") -> int:
    """Count tokens in text. Uses tiktoken if available, otherwise estimates."""
    if HAS_TIKTOKEN:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback to cl100k_base encoding
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
    else:
        # Rough estimation: ~4 characters per token
        return len(text) // 4

def print_prompt_debug(system_prompt: str, user_message: str, context: str = ""):
    if not DEBUG_PROMPTS:
        return
        
    system_tokens = count_tokens(system_prompt)
    user_tokens = count_tokens(user_message)
    total_tokens = system_tokens + user_tokens
    
    print(f"\n--- DEBUG: {context} ---")
    print(f"Tokens: System={system_tokens:,}, User={user_tokens:,}, Total={total_tokens:,}")
    print(f"System: {system_prompt[:200]}..." if len(system_prompt) > 200 else f"System: {system_prompt}")
    print(f"User: {user_message}")
    print("-" * 50)

def get_latest_user_input(history: list) -> str:
    """Returns the latest user input from the history."""
    for message in reversed(history):
        if message["role"] == "user":
            return message["content"]
    return ""

async def think(history: list, current_working_directory: str, voice_input_enabled: bool, user_info_manager=None, vector_memory_manager=None) -> dict:
    """Creates a thought and action using the ReAct prompt with relevant memory retrieval and task context."""
    from .prompts import get_task_context_string, reset_task_memory, _current_task_memory
    
    latest_user_message = get_latest_user_input(history)
    
    # Initialize task memory if this seems like a new task
    if not _current_task_memory["original_request"] or not _current_task_memory["actions_taken"]:
        reset_task_memory(latest_user_message)
    
    # Get relevant memories from vector database
    recalled_memories = []
    
    # 1. Search for relevant conversation history from vector storage
    if vector_memory_manager and latest_user_message:
        try:
            relevant_contexts = vector_memory_manager.search_relevant_context(
                query=latest_user_message,
                limit=3,
                min_similarity=0.5
            )
            for context in relevant_contexts:
                recalled_memories.append({
                    'content': context.get('content', ''),
                    'timestamp': context.get('timestamp', 'retrieved_memory')
                })
        except Exception as e:
            print(f"[Vector Memory] Error retrieving context: {e}")
    
    # 2. Get user information for context
    if user_info_manager:
        user_info_data = user_info_manager.get_user_info()
        if user_info_data:
            # Convert user info to memory format for the prompt
            for info in user_info_data[:10]:  # Limit to prevent context bloat
                recalled_memories.append({
                    'content': f"User {info['category']}: {info['key']} = {info['value']}",
                    'timestamp': info.get('timestamp', 'user_info')
                })

    BASE_PROMPT = "You are a cli-assistant that performs user's tasks with the tools you have."
    system_prompt = (
        BASE_PROMPT + "\n" + 
        get_os_info() + "\n" + 
        get_react_system_prompt(history, current_working_directory, recalled_memories, voice_input_enabled)
    )

    # Debug: Print the complete prompt being sent to LLM
    print_prompt_debug(system_prompt, latest_user_message, "MAIN THINK FUNCTION")

    try:
        response = await get_client().chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": latest_user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_response_content = response.choices[0].message.content
        decision = json.loads(raw_response_content)
        
        # If this is an action, record it in task memory for future context
        if "action" in decision:
            from .prompts import add_action_to_memory
            action = decision["action"]
            add_action_to_memory(
                tool=action.get("tool", "unknown"),
                args=action.get("args", {}),
                thought=action.get("thought", ""),
                goal=action.get("current_goal", ""),
                result=None  # Will be updated when action completes
            )
        
        # Note: save_to_memory removed - UserInfo extraction is now automatic
        
        return decision

    except Exception as e:
        print(f"Error: {e}")
        return {"text": "Sorry, an error occurred."}


def record_action_result(tool: str, args: dict, result: dict):
    """Record the result of an action in task memory."""
    from .prompts import _current_task_memory, update_task_knowledge
    
    # Update the most recent action with the result
    if _current_task_memory["actions_taken"]:
        last_action = _current_task_memory["actions_taken"][-1]
        if last_action["tool"] == tool and last_action["args"] == args:
            last_action["result"] = result
    
    # Extract useful knowledge from the result
    if result and result.get("status") == "Success":
        output = result.get("output", {})
        
        # For directory listings, store the file list
        if tool == "list_directory" and "result" in output:
            update_task_knowledge(f"files_in_{args.get('path', 'unknown')}", output["result"])
        
        # For image descriptions, store the analysis
        if tool == "describe_image" and "response" in output:
            update_task_knowledge(f"image_analysis_{args.get('image_path', 'unknown')}", output["response"])

async def reflexion(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool, vector_memory_manager=None) -> str:
    """Asks the LLM to reflect on the result of an action."""
    try:
        # Retrieve relevant memories from vector database if available
        relevant_memories = []
        if vector_memory_manager:
            try:
                # Search for relevant context based on current goal and recent actions
                search_query = f"{current_goal} {original_user_request}"
                if history:
                    # Add recent action context to search
                    recent_actions = " ".join([str(msg.get('content', ''))[:100] for msg in history[-3:]])
                    search_query += f" {recent_actions}"
                
                relevant_memories = vector_memory_manager.search_relevant_context(search_query, limit=5)
            except Exception as e:
                print(f"Warning: Could not retrieve relevant memories for reflexion: {e}")
        
        latest_user_message = get_latest_user_input(history)
        
        tool_error_detected = False
        last_observation = None
        
        # Look for the most recent observation in history
        for msg in reversed(history):
            msg_content = msg.get('content', '')
            
            # Check if this is a dictionary with observation field (new format)
            if isinstance(msg_content, dict) and 'observation' in msg_content:
                observation_text = str(msg_content['observation'])
                if any(error in observation_text for error in [
                    "Unknown tool", "unknown tool", "Unknown argument", "unknown argument",
                    "Missing required parameter", "Invalid parameter", "Tool not found",
                    "Tool execution failed", "tool execution failed"
                ]):
                    tool_error_detected = True
                    last_observation = observation_text
                break
            # Also check for old format with "Observation:" string
            elif isinstance(msg_content, str) and "Observation:" in msg_content:
                observation_text = msg_content
                if any(error in observation_text for error in [
                    "Unknown tool", "unknown tool", "Unknown argument", "unknown argument",
                    "Missing required parameter", "Invalid parameter", "Tool not found",
                    "Tool execution failed", "tool execution failed"
                ]):
                    tool_error_detected = True
                    last_observation = observation_text
                break
        
        # Use enhanced reflexion prompt if tool error detected
        if tool_error_detected:
            from ..tools.tools import get_tool_docstrings
            system_prompt = get_reflexion_prompt_with_tools(
                history, current_goal, original_user_request, voice_input_enabled, 
                last_observation, get_tool_docstrings(), relevant_memories
            )
            context = "ENHANCED REFLEXION (Tool Error Detected)"
        else:
            system_prompt = get_reflexion_prompt(history, current_goal, original_user_request, voice_input_enabled, relevant_memories)
            context = "NORMAL REFLEXION"

        # Debug: Print the complete reflexion prompt being sent to LLM
        print_prompt_debug(system_prompt, latest_user_message, context)

        response = await get_client().chat.completions.create(
            model="gpt-5-mini",
            messages= [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": latest_user_message}
            ],
            max_completion_tokens=2000,
            response_format={"type": "json_object"}
        )

        raw_response_content = response.choices[0].message.content
        # print(f"Reflexion response: {raw_response_content}")
        if not raw_response_content.strip():
            print("LLM returned an empty response for reflexion. Treating as error.")
            return {"decision": "error", "comment": "LLM returned an empty response during reflection."}
        decision = json.loads(raw_response_content)
        return decision

    except Exception as e:
        print(f"An error occurred during reflection: {e}")
        return {"decision": "error", "comment": "Sorry, an error occurred during reflection."}


async def summarize_plan_result(plan_results: list) -> str:
    """Asks the LLM to generate an ultimate response to the user prompt using the outcome of the plan's execution."""
    if not plan_results:
        return "The plan was empty or not executed."

    summary_prompt = get_final_summary_prompt(plan_results)

    try:
        response = await get_client().chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who answers the user prompt using plan execution results."},
                {"role": "user", "content": summary_prompt}
            ],
            max_completion_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred during summarization: {e}"

async def speak_text_openai(text: str):
    """
    Converts text to speech using OpenAI's TTS API and plays it.
    """
    if not text:
        print("No text to speak.")
        return

    print(f"Jarvis: {text}")
    try:
        # Generate the audio stream from the text
        response = await get_client().audio.speech.create(
            model="tts-1",          # "tts-1" is faster, "tts-1-hd" is higher quality
            voice="nova",           # Choose from 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
            input=text
        )

        # The response content is the binary audio data.
        # We read it into a BytesIO buffer to avoid saving a file to disk.
        audio_buffer = io.BytesIO(response.content)
        
        # Read the audio data from the buffer and play it
        with sf.SoundFile(audio_buffer, 'r') as sound_file:
            data = sound_file.read(dtype='float32')
            sd.play(data, sound_file.samplerate)
            sd.wait() # Wait until the audio is finished playing

    except Exception as e:
        print(f"An error occurred during text-to-speech: {e}")


async def classify_intent(user_input: str) -> str:
    """
    Uses a lightweight LLM prompt to determine if the user wants to exit.
    This is optimized for speed and token efficiency.
    """
    system_prompt = """You are an assistant that determines if the user wants to end the conversation.
Respond with only 'yes' or 'no' in lowercase.

---
Examples:

User: "goodbye"
Assistant: yes

User: "shut down now"
Assistant: yes

User: "that's all, I'm done"
Assistant: yes

User: "list all the files in my documents folder"
Assistant: no

User: "what is the capital of France?"
Assistant: no
"""

    try:
        response = await get_client().chat.completions.create(
            model="gpt-5-nano", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_completion_tokens=150,
        )
        
        decision = response.choices[0].message.content.strip().lower()
        
        # The logic is now a simple binary check.
        if decision == 'yes':
            return 'exit_program'
        else:
            # If the answer is 'no' or anything else, it's a general task.
            return 'general_task'
            
    except Exception as e:
        print(f"Error during intent classification: {e}")
        # Safest to assume the user wants to continue if the check fails.
        return "general_task"