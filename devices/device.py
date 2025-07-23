from abc import ABC, abstractmethod
from enum import Enum


class PacketType(Enum):
    BEAT = 0
    SNARE = 1
    BREAK = 2
    NEW_MUSIC = 3  # Should be on when silent and off when the music starts
    DROP = 4
    TICK = 5


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
    def __init__(self, fatal_non_discovery=True):
        success = self.scan_for_device()
        if not success and fatal_non_discovery:
            raise Exception("No device was found")
        elif not success:
            super().__init__()
            return
        success = self.init_device()
        if not success and fatal_non_discovery:
            raise Exception("The device could not be found")
        super().__init__()

    @abstractmethod
    def scan_for_device() -> bool:  # Returns if a device was found
        pass

    @abstractmethod
    def init_device() -> bool:  # Returns if the device was successfully initialized
        pass

    @property
    @abstractmethod
    def name(self):
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

    def __str__(self):
        return self.name
