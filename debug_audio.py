#!/usr/bin/env python3
import importlib.util

from lightshow.audio.audio_streams import AudioStreamHandler
from lightshow.audio.processors import SpectrumProcessor
from lightshow.utils.config import Config

if importlib.util.resolve_name("pyaudiowpatch", ""):
    import pyaudiowpatch as pyaudio  # type: ignore
else:
    try:
        import pyaudio
    except Exception:
        raise Exception("Install pyaudio!")


def debug_audio_devices():
    """List all available audio devices and their properties."""
    if pyaudio is None:
        print("PyAudio not available")
        return

    pa = pyaudio.PyAudio()
    print("\n=== Audio Devices ===")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        print(f"\nDevice {i}: {info['name']}")
        print(f"  Input Channels: {info['maxInputChannels']}")
        print(f"  Output Channels: {info['maxOutputChannels']}")
        print(f"  Sample Rate: {info['defaultSampleRate']}")
        print(f"  Default Input: {pa.get_default_input_device_info()['index'] == i}")

    pa.terminate()


def debug_audio_capture():
    """Capture and analyze raw audio data."""
    if pyaudio is None:
        print("PyAudio not available")
        return

    config = Config()
    audio_handler = AudioStreamHandler(SpectrumProcessor, config)

    print("\n=== Selected Audio Configuration ===")
    print(f"Device Index: {audio_handler.device_index}")
    print(f"Sample Rate: {audio_handler.sample_rate}")
    print(f"Channels: {audio_handler.channels}")
    print(f"Chunk Size: {audio_handler.chunk_size}")

    # Capture 10 chunks of audio
    print("\n=== Capturing Audio Samples ===")
    audio_handler.start_stream()

    samples_to_capture = 10
    chunk_count = 0

    while chunk_count < samples_to_capture:
        try:
            if not audio_handler.audio_capture:
                continue
            latest = audio_handler.audio_capture.get_latest_data()
            if latest is not None:
                print(f"\nChunk {chunk_count + 1}:")
                print(f"  Shape: {latest.shape}")
                print(f"  Dtype: {latest.dtype}")
                print(f"  Min: {latest.min():.6f}, Max: {latest.max():.6f}")
                print(f"  Mean: {latest.mean():.6f}, Std: {latest.std():.6f}")
                print(f"  Peak to Peak: {latest.max() - latest.min():.6f}")
                chunk_count += 1
        except Exception as e:
            print(f"Error: {e}")

        import time

        time.sleep(0.1)

    audio_handler.stop_stream()
    audio_handler.close()


if __name__ == "__main__":
    debug_audio_devices()
    debug_audio_capture()
