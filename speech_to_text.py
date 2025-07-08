from transformers import pipeline
import sounddevice as sd
from typing import Optional

model_name = "openai/whisper-tiny.en"
asr_pipeline = pipeline("automatic-speech-recognition", model=model_name)

def get_voice_input_whisper(duration=5, samplerate=16000) -> Optional[str]:
    print(f"Recording for {duration} seconds. Speak now...")
    try:
        # Record audio from default microphone
        audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
        sd.wait() # Wait until recording is finished

        # Transcribe the audio
        # The generate_kwargs={"task": "transcribe"} is used to specify the task for Whisper
        transcription = asr_pipeline(audio_data.squeeze(), generate_kwargs={"task": "transcribe"})
        text = transcription['text']
        print(f"You said: {text}")
        return text.strip()
    except Exception as e:
        print(f"Error during recording or transcription: {e}")
        return None
