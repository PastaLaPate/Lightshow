from abc import ABC, abstractmethod
from enum import Enum, IntEnum, StrEnum, auto
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict

from lightshow.audio.data import AudioData


class DeviceTypeName(StrEnum):
    MOVING_HEAD = "LED Moving Head"
    LAUNCHPAD_X = "Novation Launchpad X"


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


class DeviceStatus(IntEnum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()


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


class DeviceConfigType(TypedDict):
    type: DeviceTypeName
    props: dict[str, Any]


class BaseDeviceSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    id: str
    name: str = "Device X"


class AbstractAnimation(ABC):
    def __init__(self):
        self.reversed = False

    # dt: time since last frame in s
    @abstractmethod
    def next(self, audio_data: AudioData, isTick: bool = False, dt: float = 0) -> Any:
        pass

    @abstractmethod
    def reverse(self):
        self.reversed = not self.reversed
