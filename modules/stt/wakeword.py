import pvporcupine, pyaudio, struct
from my_secrets import ACCESS_KEY

KEYWORD_PATHS = ["models/Hey-Desktop_en_windows_v3_0_0.ppn"]

def init_wakeword():
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=KEYWORD_PATHS,
        sensitivities=[0.75]
    )
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    return porcupine, pa, stream

def detect_wakeword(porcupine, stream):
    pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
    pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
    return porcupine.process(pcm_unpacked)
