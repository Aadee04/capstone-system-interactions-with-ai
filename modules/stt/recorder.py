import sounddevice as sd, sys, time
from collections import deque

def record_audio_to_buffer(stop_event, buffer_queue, sample_rate, block_duration):
    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        buffer_queue.append(indata.copy())

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        callback=callback,
        blocksize=int(sample_rate * block_duration)
    ):
        while not stop_event.is_set():
            sd.sleep(50)
