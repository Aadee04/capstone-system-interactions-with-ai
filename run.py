# run.py
import sys
import threading
from queue import Queue
from dotenv import load_dotenv
import os

# Load from config/secrets.env
load_dotenv("config/secrets.env")

# now everything in secrets.env is available via os.environ


# Import STT wakeword + whisper session
from modules.stt.whisper_handler import run_stt_session
# Import LangGraph orchestrator
from app.core import run_langgraph

def main():
    print("🚀 Desktop Assistant starting...")
    print("Say the wake word to begin.")

    # A queue for communication between STT and LangGraph
    text_queue = Queue()

    # Run STT in a background thread
    def stt_worker():
        for text in run_stt_session():  # generator yields transcripts
            text_queue.put(text)

    stt_thread = threading.Thread(target=stt_worker, daemon=True)
    stt_thread.start()

    # Main loop → take transcribed text → send to LangGraph
    try:
        while True:
            text = text_queue.get()
            if not text:
                continue

            print(f"🎙 You said: {text}")
            response = run_langgraph(text)

            print(f"🤖 Assistant: {response}")

            # TODO: hook into TTS handler here to speak response

    except KeyboardInterrupt:
        print("👋 Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
