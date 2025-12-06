from collections import deque
import traceback
from typing import List, Type, Callable, Optional

import numpy as np
import pyaudiowpatch as pyaudio

from lightshow.audio.audio_types import (
    AAudioCapture,
    AAudioStreamHandler,
    AudioListener,
    Processor,
    AudioListenerType,
)
from lightshow.gui.utils.message_box import post_ui_message
from lightshow.utils.config import Config
from lightshow.utils.logger import Logger


class AudioCapture(AAudioCapture):
    """
    Collects audio data via a PyAudio callback.
    """

    def __init__(
        self,
        processor: Processor,
        stream_handler: AAudioStreamHandler,
        chunk_size=512,
        max_buffer=10,
        channels=1,
        sample_rate=44100,
    ):
        self.stream_handler = stream_handler
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
            listener = listener(self.stream_handler)
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
        self.listeners.remove(listener(self.stream_handler))

    def get_latest_data(self):
        return self.audio_buffer[-1] if self.audio_buffer else None


class AudioStreamHandler(AAudioStreamHandler):
    """
    Sets up the audio device (using WASAPI loopback when available) and manages the stream.
    """

    def __init__(self, processor: Type[Processor], config: Config):
        self.logger = Logger("AudioStreamHandler")
        self.chunk_size = config.chunk_size or 1024
        self.pyaudio_instance = pyaudio.PyAudio()
        self.processor_class = processor
        self.device_change_listeners: List[Callable[[AudioCapture], None]] = []
        self.pending_listeners = []
        # self.reinit_stream(config)

    def add_device_change_listener(self, listener: Callable[[AudioCapture], None]):
        self.device_change_listeners.append(listener)

    def reinit_stream(self, config: Config):
        """Initializes or re-initializes the stream with a new configuration."""
        self.logger.info("Initializing the stream")
        try:
            if hasattr(self, "stream") and self.stream and self.stream.is_active():
                self.stop_stream()

            self.config = config
            self.stream = None
            self.device_index = None
            self.setup_device()
            self.processor = self.processor_class(self.chunk_size, self.sample_rate)

            # Preserve listeners if AudioCapture already exists
            old_listeners = []
            if hasattr(self, "audio_capture"):
                old_listeners = self.audio_capture.listeners

            self.audio_capture = AudioCapture(
                self.processor,
                self,
                chunk_size=self.chunk_size,
                channels=self.channels,
                sample_rate=self.sample_rate,
            )
            for listener in self.device_change_listeners:
                listener(self.audio_capture)
            self.audio_capture.listeners = old_listeners
            self.logger.info("Adding the listeners")
            for listener in self.pending_listeners:
                self.audio_capture.add_listener(listener)
            self.pending_listeners = []
        except Exception:
            self.logger.error(f"Error happened during Initialization: {traceback.format_exc()}")
            post_ui_message("Audio Initialization Error", traceback.format_exc())

    def setup_device(self):
        if not self.pyaudio_instance:
            return
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
        self.logger.debug(f"Using device: {default_device['name']} (index: {self.device_index}) Sample Rate: {self.sample_rate} Hz Channels: {self.channels} Chunk size: {self.chunk_size}")

    def add_listener_on_init(
        self, listener: AudioListenerType
    ) -> Optional[AudioListener]:
        return self.pending_listeners.append(listener)

    def start_stream(self):
        try:
            if not self.pyaudio_instance:
                return
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
        except Exception:
            self.logger.error(f"Failed to start the audio stream: {traceback.format_exc()}")
            post_ui_message("Audio Stream Error", traceback.format_exc())

    def stop_stream(self):
        self.logger.info("Stopping stream")
        if hasattr(self, "stream") and self.stream is not None:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def close(self):
        """Stops the stream and terminates the PyAudio instance."""
        self.stop_stream()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
