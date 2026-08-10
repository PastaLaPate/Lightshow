from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PacketType(Enum):
    # Output [0, 255]
    BEAT = 0
    SNARE = 1
    BREAK = 2
    NEW_MUSIC = 3  # Should be on when silent and off when the music starts
    DROP = 4
    TICK = 5
    PAUSE = 6
    FLICKER = 7
    # Input [256, 511]
    MANUAL_MODE = 256
    AUTO_TICK = 257  # Enables/Disables auto ticking, useful when in manual mode


class PacketStatus(Enum):
    ON = 0
    OFF = 1


class PacketData:
    def __init__(
        self,
        packet_type: PacketType,
        packet_status: PacketStatus,
        power: int = 1,
        audio_data=None,
    ):
        self.packet_type = packet_type
        self.packet_status = packet_status
        self.power = power  # Used to determine the brightness of the LED
        self.audio_data = (
            audio_data  # Optional AudioData object for audio-reactive effects
        )


class Device[T: BaseModel, R: BaseModel](ABC):
    DEVICE_TYPE_NAME = "DUMMY DEVICE"

    CONFIG_SCHEMA: type[T]
    RUNTIME_SCHEMA: type[R] | None

    def __init__(self, config: T):
        self.ready = False
        self.device_name = ""
        self.config = config
        self.runtime = self.RUNTIME_SCHEMA() if self.RUNTIME_SCHEMA else None

        super().__init__()

    def connect(self, fatal_non_discovery=True):
        success = self.scan_for_device()
        if not success and fatal_non_discovery:
            raise ConnectionError("No device was found")
        elif not success:
            return
        success = self.init_device()
        if not success and fatal_non_discovery:
            raise ConnectionRefusedError("The device could not be found")
        self.ready = success
        return

    @abstractmethod
    def disconnect(self):
        self.ready = False

    @abstractmethod
    def scan_for_device(self) -> bool:  # Returns if a device was found
        pass

    @abstractmethod
    def init_device(self) -> bool:  # Returns if the device was successfully initialized
        pass

    # Name, data
    @abstractmethod
    def save(self) -> tuple[str, dict[str, Any]]:
        return self.DEVICE_TYPE_NAME, self.config.model_dump()

    # Returns if correctly loaded
    @abstractmethod
    def load(self, data: tuple[str, dict[str, Any]]) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def hsv_to_rgb(self, h: float, s: float, v: float, a: float) -> tuple:
        if s:
            if h == 1.0:
                h = 0.0
            i = int(h * 6.0)
            f = h * 6.0 - i

            w = v * (1.0 - s)
            q = v * (1.0 - s * f)
            t = v * (1.0 - s * (1.0 - f))

            if i == 0:
                return (v, t, w, a)
            if i == 1:
                return (q, v, w, a)
            if i == 2:
                return (w, v, t, a)
            if i == 3:
                return (w, q, v, a)
            if i == 4:
                return (t, w, v, a)
            if i == 5:
                return (v, w, q, a)
        else:
            return (v, v, v, a)
        return (0, 0, 0, a)

    def __str__(self):
        return self.name or "Device"


class OutputDevice(Device):
    @abstractmethod
    def on(self, packet: PacketData):
        pass


class InputDevice(Device):
    def __init__(self):
        super().__init__()
