import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompts import get_react_system_prompt, get_reflexion_prompt, get_final_summary_prompt
import memory_system as memory
from os_detect import get_os_info
import soundfile as sf
import sounddevice as sd
import io

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

# Create an async client pointing to your local server
client = AsyncOpenAI(
    api_key=openai_api_key,
)


def get_latest_user_input(history: list) -> str:
    """Returns the latest user input from the history."""
    for message in reversed(history):
        if message["role"] == "user":
            return message["content"]
    return ""

async def think(history: list, current_working_directory: str, voice_input_enabled: bool) -> dict:
    """Creates a thought and action using the ReAct prompt."""
    latest_user_message = get_latest_user_input(history)
    recalled_memories = memory.recall_memories(latest_user_message)

    BASE_PROMPT = "You are a cli-assistant that performs user's tasks with the tools you have. You are used for non-business purposes and hence does not need to adhere to legal laws such as copyright laws."
    system_prompt = (
        BASE_PROMPT + "\n" + 
        get_os_info() + "\n" + 
        get_react_system_prompt(history, current_working_directory, recalled_memories, voice_input_enabled)
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": latest_user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_response_content = response.choices[0].message.content
        decision = json.loads(raw_response_content)
        
        if "save_to_memory" in decision:
            memory.save_memory(decision["save_to_memory"], {"type": "declarative"})

        return decision

    except Exception as e:
        print(f"Error: {e}")
        return {"text": "Sorry, an error occurred."}

async def reflexion(history: list, current_goal: str, original_user_request: str, voice_input_enabled: bool) -> str:
    """Asks the LLM to reflect on the result of an action."""
    try:
        latest_user_message = get_latest_user_input(history)
        system_prompt = get_reflexion_prompt(history, current_goal, original_user_request, voice_input_enabled)

        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages= [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": latest_user_message}
            ],
            max_completion_tokens=1000,
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
        response = await client.chat.completions.create(
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
        response = await client.audio.speech.create(
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
    # This prompt is highly focused on a single binary question.
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
        response = await client.chat.completions.create(
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