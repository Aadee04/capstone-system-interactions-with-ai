import os, torch

USE_CUDA = torch.cuda.is_available()

if not USE_CUDA:
    os.environ["OMP_NUM_THREADS"] = str(os.cpu_count())
    torch.set_num_threads(os.cpu_count())

SAMPLE_RATE = 16000

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
