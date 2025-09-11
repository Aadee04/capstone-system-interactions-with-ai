from pathlib import Path
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import struct
import torch
import sys
import contextlib
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import tempfile
import os
import soundfile as sf
import time
import threading
from collections import deque
import gc

# GPU / CPU Check 
USE_CUDA = torch.cuda.is_available()

# CPU-specific optimizations
if not USE_CUDA:
    os.environ["OMP_NUM_THREADS"] = str(os.cpu_count())
    torch.set_num_threads(os.cpu_count())

# Wake Word Config
env_path = Path(__file__).resolve().parent.parent.parent / "config" / "secrets.env"

if not env_path.exists():
    print("Missing secrets.env in config/. Please create it with your ACCESS_KEY.")
    sys.exit(1)
load_dotenv(env_path)

if not os.getenv("ACCESS_KEY"):
    print("ACCESS_KEY not found in secrets.env.")
    sys.exit(1)
print("Secrets loaded successfully!")

ACCESS_KEY = os.getenv("ACCESS_KEY")

# Porcupine wakeword path
keyword_paths = ['resources/wakeword/Hey-Desktop_en_windows_v3_0_0.ppn']

# Model + VAD Config based on device
if USE_CUDA:
    MODEL_SIZE = "large-v3"
    BLOCK_DURATION = 5.0
    SILENCE_TIMEOUT = 8.0
    DEVICE = "cuda"
    COMPUTE_TYPE = "float16"
else:
    MODEL_SIZE = "base"
    BLOCK_DURATION = 3.0
    SILENCE_TIMEOUT = 5.0
    DEVICE = "cpu"
    COMPUTE_TYPE = "int8"

SAMPLE_RATE = 16000

# Load VAD
vad_model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload=False,
    trust_repo=True
)
get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils

# Wake Word Init
porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=keyword_paths,
    sensitivities=[0.75]
)
pa = pyaudio.PyAudio()
wake_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

# Audio Recording 
def record_audio_to_buffer(stop_event, buffer_queue):
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        buffer_queue.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        callback=audio_callback,
                        blocksize=int(SAMPLE_RATE * BLOCK_DURATION)):
        while not stop_event.is_set():
            sd.sleep(50)

# Audio Processing
def process_audio_stream(model, buffer_queue, stop_event):
    last_speech_time = time.time()

    while not stop_event.is_set():
        if buffer_queue:
            audio_chunk = buffer_queue.popleft()
        else:
            if time.time() - last_speech_time > SILENCE_TIMEOUT:
                print("Silence detected. Returning to wake word mode.")
                break
            time.sleep(0.05)
            continue

        wav_tensor = torch.from_numpy(audio_chunk).float().squeeze()
        speech_timestamps = get_speech_timestamps(wav_tensor, vad_model, sampling_rate=SAMPLE_RATE)
        if not speech_timestamps:
            continue

        last_speech_time = time.time()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            wav_path = tmpfile.name
        sf.write(wav_path, audio_chunk, SAMPLE_RATE)

        segments, _ = model.transcribe(wav_path, language="en")
        text = " ".join([seg.text for seg in segments]).strip()
        if text:
            print(f"You said: {text}")

        os.remove(wav_path)

# Run Whisper Session
def run_whisper_session():
    print("Wake word detected! Starting session...")
    buffer_queue = deque()
    stop_event = threading.Event()
    record_thread = threading.Thread(target=record_audio_to_buffer, args=(stop_event, buffer_queue))
    record_thread.start()

    model = None
    try:
        # Load model only when wake word is detected
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print(f"Model loaded on {DEVICE}.")

        process_audio_stream(model, buffer_queue, stop_event)

    except KeyboardInterrupt:
        print("CTRL+C detected. Exiting program...")
        stop_event.set()
        # Propagate KeyboardInterrupt to main loop
        raise

    except Exception as e:
        print(f"Error during transcription: {e}")

    finally:
        stop_event.set()
        record_thread.join()
        # Remove model if it was successfully loaded
        if model is not None:
            del model
            import gc
            gc.collect()
            print("Whisper model unloaded from memory.")


# Wake Word Listener
print("Listening for wake word...")
try:
    while True:
        pcm = wake_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
        result = porcupine.process(pcm_unpacked)

        if result >= 0:
            run_whisper_session()

except KeyboardInterrupt:
    print("Stopping program...")

finally:
    with contextlib.suppress(Exception):
        if wake_stream.is_active():
            wake_stream.stop_stream()
    with contextlib.suppress(Exception):
        wake_stream.close()
    with contextlib.suppress(Exception):
        pa.terminate()
    with contextlib.suppress(Exception):
        porcupine.delete()
    print("Stopped.")


def start_stt_loop():
    """Start listening for wake word and run Whisper session."""
    print("Listening for wake word...")
    try:
        while True:
            pcm = wake_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm_unpacked)

            if result >= 0:
                run_whisper_session()

    except KeyboardInterrupt:
        print("Stopping program...")

    finally:
        with contextlib.suppress(Exception):
            if wake_stream.is_active():
                wake_stream.stop_stream()
        with contextlib.suppress(Exception):
            wake_stream.close()
        with contextlib.suppress(Exception):
            pa.terminate()
        with contextlib.suppress(Exception):
            porcupine.delete()
        print("Stopped.")
