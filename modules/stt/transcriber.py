import os, tempfile, soundfile as sf
from faster_whisper import WhisperModel
from stt.vad import get_speech_timestamps

def transcribe_chunk(model, audio_chunk, sample_rate, vad_model):
    wav_tensor = audio_chunk.squeeze()
    speech_timestamps = get_speech_timestamps(wav_tensor, vad_model, sampling_rate=sample_rate)
    if not speech_timestamps:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
        wav_path = tmpfile.name
    sf.write(wav_path, audio_chunk, sample_rate)

    segments, _ = model.transcribe(wav_path, language="en")
    os.remove(wav_path)

    return " ".join([seg.text for seg in segments]).strip()
