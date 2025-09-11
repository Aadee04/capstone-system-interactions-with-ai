from modules.stt import transciption
from queue import Queue
from dotenv import load_dotenv
import os

# Load from config/secrets.env
load_dotenv("config/secrets.env")


if __name__ == "__main__":
    transciption.start_stt_loop()
