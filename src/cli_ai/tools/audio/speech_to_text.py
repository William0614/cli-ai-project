import torch
import numpy as np
from transformers import pipeline
import sounddevice as sd
from typing import Optional
from ...utils.spinner import Spinner
from colorama import init, Fore

model_name = "openai/whisper-tiny.en"
asr_pipeline = pipeline("automatic-speech-recognition", model=model_name)

# --- Silero VAD Setup ---
try:
    vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False)
    (get_speech_timestamps,
     save_audio,
     read_audio,
     VADIterator,
     collect_chunks) = utils
except Exception as e:
    print(f"Error loading Silero VAD model: {e}")
    print("Please check your internet connection and PyTorch installation.")
    vad_model = None

def get_voice_input_whisper(samplerate=16000) -> Optional[str]:

    if not vad_model:
        print("VAD model is not available. Please check your setup.")
        return None
    
    # --------- Adjustable Parameters ---------
    VAD_THRESHOLD = 0.5 # Threshold for voice activity detection
    SILENCE_DURATION_S = 1 # Duration of silence to consider before stopping recording
    PRE_SPEECH_BUFFER = 0.25 # Buffer time before speech starts to avoid cutting off the beginning

    chunk_size = 512
    silence_chunks = int(SILENCE_DURATION_S * samplerate / chunk_size) # Number of chunks to consider silence before stopping
    pre_speech_chunks = int(PRE_SPEECH_BUFFER * samplerate / chunk_size)  # Buffer before speech starts

    recorded_chunks = []
    pre_speech_buffer = []
    is_recording = False
    silence_counter = 0

    print(Fore.CYAN + f"Listening... (Speak to start recording)")

    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='float32', blocksize=chunk_size) as stream:
            while True:
                audio_chunk, overflowed = stream.read(chunk_size)

                audio_chunk_tensor = torch.from_numpy(audio_chunk).squeeze()

                speech_prob = vad_model(audio_chunk_tensor, samplerate).item()

                if speech_prob > VAD_THRESHOLD:
                    if not is_recording:
                        spinner = Spinner("Starting recording...")
                        spinner.start()
                        is_recording = True
                        recorded_chunks.extend(pre_speech_buffer)  # Add pre-speech buffer to recorded chunks

                    recorded_chunks.append(audio_chunk_tensor)
                    silence_counter = 0
                else:
                    if is_recording:
                        silence_counter += 1
                        if silence_counter > silence_chunks:
                            spinner.stop()
                            break
                    else:
                        pre_speech_buffer.append(audio_chunk_tensor)
                        if len(pre_speech_buffer) > pre_speech_chunks:
                            pre_speech_buffer.pop(0)
            
            if not recorded_chunks:
                print("No speech detected.")
                return None

        # print("Transcribing...")
        # Record audio from default microphone
        audio_data = np.concatenate(recorded_chunks, axis=0).squeeze()

        transcription = asr_pipeline(audio_data)
        text = transcription['text']

        return text.strip()

    except KeyboardInterrupt:
        print(Fore.RED + "\nRecording interrupted by user.")
        return None
    except Exception as e:
        print(Fore.RED + f"An error occurred: {e}")
        return None
