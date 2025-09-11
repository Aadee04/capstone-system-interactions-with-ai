import torch

vad_model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
    trust_repo=True
)

get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils
