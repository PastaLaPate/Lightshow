from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Callable, Type, Union

import numpy as np

from lightshow.audio.data import AudioData
from lightshow.utils.config import Config

# sounddevice exposes this type but it's just an int-like object;
# using Any keeps the ABC free of a hard sounddevice dependency.
CallbackFlags = Any


class Processor(ABC):
    def __init__(self, chunk_size: int, sample_rate: int):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        super().__init__()

    @abstractmethod
    def process(self, data: np.ndarray) -> AudioData:
        pass


class AAudioCapture(ABC):
    def __init__(
        self,
        processor: Processor,
        chunk_size: int = 512,
        max_buffer: int = 10,
        channels: int = 1,
        sample_rate: int = 44100,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_buffer: deque = deque(maxlen=max_buffer)
        self.channels = channels

    @abstractmethod
    def callback(
        self,
        in_data: np.ndarray,
        frames: int,
        time_info: Any,
        status: CallbackFlags,
    ) -> None:
        pass


class AAudioStreamHandler(ABC):
    def __init__(self, processor: Type[Processor], config: Config):
        pass

    @abstractmethod
    def reinit_stream(self, config: Config) -> None:
        pass

    @abstractmethod
    def add_device_change_listener(
        self, listener: Callable[["AAudioCapture"], None]
    ) -> None:
        pass

    @abstractmethod
    def setup_device(self) -> None:
        pass

    @abstractmethod
    def start_stream(self) -> None:
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class AudioListener(ABC):
    def __init__(self, stream_handler: AAudioStreamHandler):
        self.stream_handler = stream_handler
        self.stream_handler.add_device_change_listener(self.on_device_change)
        self.channels: int = 1
        self.chunk_size: int = 1024
        self.sample_rate: int = 44100
        super().__init__()

    def on_device_change(self, capture: AAudioCapture) -> None:
        self.channels = capture.channels
        self.chunk_size = capture.chunk_size
        self.sample_rate = capture.sample_rate

    @abstractmethod
    def __call__(self, data: AudioData) -> bool:
        """Return False to unsubscribe this listener."""
        pass


AudioListenerType = Union[AudioListener, Callable[[AudioData], bool]]
