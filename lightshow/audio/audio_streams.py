from collections import deque
from typing import List, Type, Callable, Optional

import numpy as np
import pyaudiowpatch as pyaudio

from lightshow.audio.audio_types import (
    AudioData,
    AudioListener,
    Processor,
    AudioListenerType,
)
from lightshow.utils.config import Config


class AudioCapture:
    """
    Collects audio data via a PyAudio callback.
    """

    def __init__(
        self,
        processor: Processor,
        chunk_size=512,
        max_buffer=10,
        channels=1,
        sample_rate=44100,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_buffer = deque(maxlen=max_buffer)
        self.channels = channels  # default is 1
        self.processor = processor
        self.listeners: List[AudioListenerType] = []

    def callback(self, in_data, frame_count, time_info, status):
        # Convert incoming bytes into a NumPy array of int16.
        data = np.frombuffer(in_data, dtype=np.int16)
        # If multiple channels are present, reshape and take the first channel.
        if self.channels > 1:
            try:
                data = data.reshape(-1, self.channels)[:, 0]
            except ValueError:
                data = data[: self.chunk_size]
        else:
            data = data[: self.chunk_size]
        treatedData = self.processor.process(data)
        for listener in self.listeners:
            if not listener(treatedData):
                self.listeners.remove(listener)
        self.audio_buffer.append(data)
        return (in_data, pyaudio.paContinue)

    def add_listener(self, listener: AudioListenerType) -> Optional[AudioListener]:
        """
        Returns the listener instanced if it was initialy a class.
        """

        if isinstance(listener, type) and issubclass(listener, AudioListener):
            listener = listener(self.channels, self.chunk_size, self.sample_rate)
            self.listeners.append(listener)
            return listener
        elif isinstance(listener, AudioListener):
            self.listeners.append(listener)
        elif isinstance(listener, Callable):  # Lambda function
            self.listeners.append(listener)
        else:
            raise ValueError(
                "Listener must be an AudioListener instance, class or a lambda function"
            )
        return None

    def remove_listener(self, listener: Type[AudioListener]):
        if not issubclass(listener, AudioListener):
            raise ValueError("Listener must be an instance of AudioListener")
        self.listeners.remove(
            listener(self.channels, self.chunk_size, self.sample_rate)
        )

    def get_latest_data(self):
        return self.audio_buffer[-1] if self.audio_buffer else None


class AudioStreamHandler:
    """
    Sets up the audio device (using WASAPI loopback when available) and manages the stream.
    """

    def __init__(self, processor: Type[Processor], config: Config):
        self.chunk_size = config.chunk_size
        self.pyaudio_instance = pyaudio.PyAudio()
        self.config = config
        self.stream = None
        self.device_index = None
        self.setup_device()
        self.processor = processor(self.chunk_size, self.sample_rate)
        self.audio_capture = AudioCapture(
            self.processor,
            chunk_size=self.chunk_size,
            channels=self.channels,
            sample_rate=self.sample_rate,
        )

    def setup_device(self):
        try:
            wasapi_info = self.pyaudio_instance.get_host_api_info_by_type(
                pyaudio.paWASAPI
            )
        except OSError:
            raise Exception("WASAPI is not available on the system. Exiting...")

        if self.config.device_index == -1:
            default_device = self.pyaudio_instance.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )
            if not default_device["isLoopbackDevice"]:
                for (
                    loopback
                ) in self.pyaudio_instance.get_loopback_device_info_generator():
                    if default_device["name"] in loopback["name"]:
                        default_device = loopback
                        break
                else:
                    raise Exception(
                        "Default loopback output device not found.\n\n"
                        "Run `python -m pyaudiowpatch` to check available devices.\nExiting..."
                    )
        else:
            default_device = self.pyaudio_instance.get_device_info_by_index(
                self.config.device_index
            )
            if not default_device["isLoopbackDevice"]:
                raise Exception(
                    f"Device {self.config.device_index} is not a loopback device.\n"
                    "Run `python -m pyaudiowpatch` to check available devices.\nExiting..."
                )
        self.device_index = default_device["index"]
        self.sample_rate = int(default_device["defaultSampleRate"])
        self.channels = default_device["maxInputChannels"]
        print(
            f"Using device: {default_device['name']} (index: {self.device_index}) Sample Rate: {self.sample_rate} Hz Channels: {self.channels} Chunk size: {self.chunk_size}"
        )

    def start_stream(self):
        self.stream = self.pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            frames_per_buffer=self.chunk_size,
            input=True,
            input_device_index=self.device_index,
            stream_callback=self.audio_capture.callback,
        )
        self.stream.start_stream()

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.pyaudio_instance.terminate()
