from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Tuple


class PacketType(Enum):
    BEAT = 0
    SNARE = 1
    BREAK = 2
    NEW_MUSIC = 3  # Should be on when silent and off when the music starts
    DROP = 4
    TICK = 5
    PAUSE = 6


class PacketStatus(Enum):
    ON = 0
    OFF = 1


class PacketData:
    def __init__(
        self, packet_type: PacketType, packet_status: PacketStatus, power: int = 1
    ):
        self.packet_type = packet_type
        self.packet_status = packet_status
        self.power = power  # Used to determine the brightness of the LED


class Device(ABC):
    DEVICE_TYPE_NAME = "DUMMY DEVICE"

    EDITABLE_PROPS = []

    def __init__(self):
        self.ready = False
        self.device_name = ""
        super().__init__()

    def connect(self, fatal_non_discovery=True):
        success = self.scan_for_device()
        if not success and fatal_non_discovery:
            raise Exception("No device was found")
        elif not success:
            return
        success = self.init_device()
        if not success and fatal_non_discovery:
            raise Exception("The device could not be found")
        self.ready = success
        return

    @abstractmethod
    def disconnect(self):
        self.ready = False
        return

    @abstractmethod
    def scan_for_device(self) -> bool:  # Returns if a device was found
        pass

    @abstractmethod
    def init_device(self) -> bool:  # Returns if the device was successfully initialized
        pass

    # Name, data
    @abstractmethod
    def save(self) -> Tuple[str, dict[str, Any]]:
        pass

    # Returns if correctly loaded
    @abstractmethod
    def load(self, data: Tuple[str, dict[str, Any]]) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def on(self, packet: PacketData):
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
