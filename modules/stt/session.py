import time, threading, torch, gc
from collections import deque
from stt import config
from stt.recorder import record_audio_to_buffer
from stt.transcriber import transcribe_chunk
from stt.vad import vad_model
from faster_whisper import WhisperModel

def run_whisper_session():
    buffer_queue = deque()
    stop_event = threading.Event()
    record_thread = threading.Thread(
        target=record_audio_to_buffer,
        args=(stop_event, buffer_queue, config.SAMPLE_RATE, config.BLOCK_DURATION)
    )
    record_thread.start()

    model = WhisperModel(config.MODEL_SIZE, device=config.DEVICE, compute_type=config.COMPUTE_TYPE)
    print(f"Model loaded on {config.DEVICE}.")

    last_speech_time = time.time()

    try:
        while not stop_event.is_set():
            if buffer_queue:
                audio_chunk = buffer_queue.popleft()
                text = transcribe_chunk(model, audio_chunk, config.SAMPLE_RATE, vad_model)
                if text:
                    print(f"You said: {text}")
                last_speech_time = time.time()
            else:
                if time.time() - last_speech_time > config.SILENCE_TIMEOUT:
                    print("Silence detected. Returning to wake word mode.")
                    break
                time.sleep(0.05)

    finally:
        stop_event.set()
        record_thread.join()
        del model
        gc.collect()
        print("Whisper model unloaded from memory.")
