from collections import deque
from typing import Tuple, Type, Union, Callable
from abc import ABC, abstractmethod
from typing_extensions import Buffer
import numpy as np

from lightshow.utils.config import Config


class AudioData:
    def __init__(self, power_spectrum, mel_energies):
        self.power_spectrum = power_spectrum
        self.mel_energies = mel_energies

    def get_ps_mean(self, range):
        if len(range) > 2:
            raise ValueError("Range must be a list of two elements.")
        return np.mean(self.power_spectrum[range[0] : range[1]])

    def get_mel_mean(self, range):
        if len(range) > 2:
            raise ValueError("Range must be a list of two elements.")
        return np.mean(self.mel_energies[range[0] : range[1]])


class Processor(ABC):

    def __init__(self, chunk_size, sample_rate):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        super().__init__()

    @abstractmethod
    def process(self, data) -> AudioData:
        pass


class AAudioCapture(ABC):

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
        self.channels = channels

    @abstractmethod
    def callback(
        self, in_data: Buffer, frame_count, time_info, status
    ) -> Tuple[Buffer, int]:
        pass


class AAudioStreamHandler(ABC):
    def __init__(self, processor: Type[Processor], config: Config):
        pass

    @abstractmethod
    def reinit_stream(self, config: Config):
        pass

    @abstractmethod
    def add_device_change_listener(self, listener: Callable[[AAudioCapture], None]):
        pass

    @abstractmethod
    def setup_device(self):
        pass

    @abstractmethod
    def start_stream(self):
        pass

    @abstractmethod
    def stop_stream(self):
        pass

    @abstractmethod
    def close(self):
        pass


class AudioListener(ABC):

    def __init__(self, AudioStreamHandler: AAudioStreamHandler):
        self.stream_handler = AudioStreamHandler
        self.stream_handler.add_device_change_listener(self.on_device_change)
        self.channels = 1
        self.chunk_size = 1024
        self.sample_rate = 44100
        super().__init__()

    def on_device_change(self, capture: AAudioCapture):
        self.channels = capture.channels
        self.chunk_size = capture.chunk_size
        self.sample_rate = capture.sample_rate

    @abstractmethod
    def __call__(
        self, data: AudioData
    ) -> bool:  # Return False if the listener wants to stop listening
        pass


AudioListenerType = Union[AudioListener, Callable[[AudioData], bool]]
