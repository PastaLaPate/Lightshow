from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Callable, Type, Union

import numpy as np
import soundcard as sc

from lightshow.audio.data import AudioData

# sounddevice exposes this type but it's just an int-like object;
# using Any keeps the ABC free of a hard sounddevice dependency.
CallbackFlags = Any


class AudioDevice:
    def __init__(self, name: str | None = None, is_default=False, is_loopback=False):
        if name is None and not is_default:
            raise ValueError("Must provide a name for non-default devices")
        self.is_loopback = is_loopback
        self.is_default = is_default
        self.name = name
        self._device = None  # Soundcard device object, populated by fetch_device()

    @property
    def device(self):
        if self._device is None:
            self.fetch_device()
        return self._device

    def fetch_device(self):
        """
        Forces the find and store the actual soundcard device.
        Called automatically by the device property when needed, but can be called manually to refresh the device.
        Tries to find the actual device based on the name, is default and loopback flags.
        """
        device_list = (
            [d for d in sc.all_microphones(include_loopback=True) if d.isloopback]
            if self.is_loopback
            else sc.all_microphones()
        )
        if self.is_default:
            if self.is_loopback:
                # Loopback devices have the same name as their corresponding speaker,
                # so we need to find the default speaker first.
                # Then we look for a microphone loopback device with the same name.
                speaker = sc.default_speaker()
                self.name = speaker.name
                print("help")
                self._device = self._find_in_device_list(device_list, speaker.name)
                print(self._device.name)
            else:
                # Just gets the default mic.
                self._device = sc.default_microphone()
                self.name = self._device.name
        else:
            # Just find the device with the specified name. If in loopback mode, uses the loopback only device list. Else uses the normal mic list without loopback devices.
            self._device = self._find_in_device_list(device_list, self.name)

    def _find_in_device_list(self, device_list, name):
        for device in device_list:
            if name in device.name or device.name == name:
                return device
        raise ValueError(f"Device with name '{name}' not found")

    def to_dict(self) -> dict:
        return {
            "name": self.name
            if not self.is_default
            else None,  # Do not save the name of the default device since it can change across systems and sessions. Instead, we will identify it by the is_default flag when deserializing.
            "is_default": self.is_default,
            "is_loopback": self.is_loopback,
        }

    @staticmethod
    def from_dict(data) -> "AudioDevice":
        name = data.get("name")
        is_default = data.get("is_default", False)
        if not name and not is_default:
            raise ValueError(f"Invalid AudioDevice dict: {data}")
        return AudioDevice(
            name=name, is_default=is_default, is_loopback=data.get("is_loopback", False)
        )


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
    def __init__(self, processor: Type[Processor]):
        pass

    @abstractmethod
    def reinit_stream(self) -> None:
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
