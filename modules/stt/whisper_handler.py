from dotenv import load_dotenv
import sys
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

# ===== Detect device =====
USE_CUDA = torch.cuda.is_available()

# ===== CPU Optimization =====
if not USE_CUDA:
    os.environ["OMP_NUM_THREADS"] = str(os.cpu_count())
    torch.set_num_threads(os.cpu_count())

keyword_paths = ['resources/wakewords/Hey-Desktop_en_windows_v3_0_0.ppn']

# ===== Model + VAD Config =====
if USE_CUDA:
    MODEL_SIZE = "large-v3"
    BLOCK_DURATION = 5.0
    SILENCE_TIMEOUT = 8.0
    DEVICE = "cuda"
    COMPUTE_TYPE = "float16"
else:
    MODEL_SIZE = "base"
    BLOCK_DURATION = 1.0
    SILENCE_TIMEOUT = 5.0
    DEVICE = "cpu"
    COMPUTE_TYPE = "int8"

SAMPLE_RATE = 16000

# Build path relative to project root
env_path = Path(__file__).resolve().parent.parent / "config" / "secrets.env"

if not env_path.exists():
    print("Missing secrets.env in config/. Please create it with your ACCESS_KEY.")
    sys.exit(1)

load_dotenv(env_path)

# Example: check that key is loaded
if not os.getenv("ACCESS_KEY"):
    print("ACCESS_KEY not found in secrets.env.")
    sys.exit(1)

print("Secrets loaded successfully!")

ACCESS_KEY = os.getenv("ACCESS_KEY")

# ===== Wake Word Init =====
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

# ===== Audio Recording =====
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

# ===== Audio Processing =====
def process_audio_stream(model, buffer_queue, stop_event):
    last_speech_time = time.time()

    while not stop_event.is_set():
        if buffer_queue:
            audio_chunk = buffer_queue.popleft()
        else:
            if time.time() - last_speech_time > SILENCE_TIMEOUT:
                return  # silence timeout
            time.sleep(0.05)
            continue

        # save chunk
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            wav_path = tmpfile.name
        sf.write(wav_path, audio_chunk, SAMPLE_RATE)

        # transcribe
        segments, _ = model.transcribe(wav_path, language="en")
        text = " ".join([seg.text for seg in segments]).strip()
        os.remove(wav_path)

        if text:
            yield text  # <--- key difference vs old script

        last_speech_time = time.time()

# ===== Main session =====
def run_stt_session():
    """
    Generator that yields text after wake word detection.
    """
    print("🎧 Listening for wake word...")
    try:
        while True:
            pcm = wake_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm_unpacked)

            if result >= 0:
                print("🔔 Wake word detected!")
                buffer_queue = deque()
                stop_event = threading.Event()
                record_thread = threading.Thread(
                    target=record_audio_to_buffer,
                    args=(stop_event, buffer_queue)
                )
                record_thread.start()

                model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

                try:
                    for text in process_audio_stream(model, buffer_queue, stop_event):
                        yield text
                finally:
                    stop_event.set()
                    record_thread.join()
                    del model
                    torch.cuda.empty_cache() if USE_CUDA else None
                    print("📴 Whisper session ended. Back to wake word mode.")

    except KeyboardInterrupt:
        print("👋 Exiting STT...")
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



if __name__ == "__main__":

    run_stt_session()
    print("STT session ended.")