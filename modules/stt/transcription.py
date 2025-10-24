from pathlib import Path
from dotenv import load_dotenv
import pvporcupine
import pyaudio
import struct
import sys
import contextlib
import time
import threading
import os


try:
    import speech_recognition as sr
except ImportError:
    print("Installing speech_recognition...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "speechrecognition", "pyaudio"])
    import speech_recognition as sr

# Windows Speech Recognition Setup
recognizer = sr.Recognizer()
microphone = sr.Microphone()

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

# Configuration for Windows Speech Recognition
SILENCE_TIMEOUT = 5.0  # seconds to wait for speech before returning to wake word mode
LISTEN_TIMEOUT = 1.0   # timeout for each recognition attempt

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

# Windows Speech Recognition Session
def run_windows_speech_recognition():
    """Use Windows Speech Recognition for transcription after wake word"""
    print("Starting Windows Speech Recognition session...")
    
    # Adjust microphone for ambient noise
    print("Adjusting microphone for ambient noise...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    session_start_time = time.time()
    consecutive_failures = 0
    max_failures = 3
    
    while True:
        try:
            # Check if we should exit due to silence timeout
            if time.time() - session_start_time > SILENCE_TIMEOUT:
                print("Session timeout. Returning to wake word mode.")
                break
                
            print("Listening for speech...")
            
            # Listen for audio input
            with microphone as source:
                try:
                    # Listen with timeout
                    audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=5)
                    session_start_time = time.time()  # Reset timeout on successful audio capture
                except sr.WaitTimeoutError:
                    continue  # No audio captured, continue listening
            
            # Try to recognize speech using Windows Speech Recognition
            try:
                text = recognizer.recognize_windows(audio)
                if text.strip():
                    print(f"You said: {text}")
                    consecutive_failures = 0
                    # Here you could send the text to your agent system
                    
            except sr.UnknownValueError:
                print("Could not understand audio")
                consecutive_failures += 1
            except sr.RequestError as e:
                print(f"Windows Speech Recognition error: {e}")
                consecutive_failures += 1
            
            # Exit if too many consecutive failures
            if consecutive_failures >= max_failures:
                print("Too many recognition failures. Returning to wake word mode.")
                break
                
        except KeyboardInterrupt:
            print("CTRL+C detected. Exiting speech recognition session...")
            break
        except Exception as e:
            print(f"Error in speech recognition session: {e}")
            break

# Run Speech Recognition Session
def run_speech_recognition_session():
    print("Wake word detected! Starting Windows Speech Recognition session...")
    
    try:
        run_windows_speech_recognition()

    except KeyboardInterrupt:
        print("CTRL+C detected. Exiting program...")
        # Propagate KeyboardInterrupt to main loop
        raise

    except Exception as e:
        print(f"Error during speech recognition: {e}")

    finally:
        print("Speech recognition session ended. Returning to wake word detection.")


# Wake Word Listener
print("Listening for wake word...")
try:
    while True:
        pcm = wake_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
        result = porcupine.process(pcm_unpacked)

        if result >= 0:
            run_speech_recognition_session()

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
    """Start listening for wake word and run Windows Speech Recognition session."""
    print("Listening for wake word...")
    try:
        while True:
            pcm = wake_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm_unpacked)

            if result >= 0:
                run_speech_recognition_session()

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
