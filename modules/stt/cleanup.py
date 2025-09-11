import contextlib

def cleanup(porcupine, pa, stream):
    with contextlib.suppress(Exception):
        if stream.is_active():
            stream.stop_stream()
    with contextlib.suppress(Exception):
        stream.close()
    with contextlib.suppress(Exception):
        pa.terminate()
    with contextlib.suppress(Exception):
        porcupine.delete()
    print("Stopped.")
