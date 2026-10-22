from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, NamedTuple, TypedDict

from pydantic import BaseModel, ConfigDict


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


class ServoAngles(NamedTuple):
    base: int
    top: int


@dataclass
class FixtureCalibration:
    base_range: tuple[float, float] = (0, 120)
    top_range: tuple[float, float] = (0, 70)
    base_offset: float = 0
    invert_base: bool = False
    invert_top: bool = False
    servo_limits: tuple[float, float] = (0, 180)

    def to_servo(self, x: float, y: float) -> ServoAngles:
        """Converts normalized angles to real ranged angles

        Args:
            x (float): [-1,1] Where -1 is lower bound and 1 upper bound. For base angle.
            y (float): [-1,1] Where -1 is lower bound and 1 upper bound. For head angle.

        Returns:
            tuple[int, int]: _description_
        """
        x = max(-1, min(1, x))
        y = max(-1, min(1, y))
        if self.invert_base:
            x = -x
        if self.invert_top:
            y = -y

        lo, hi = self.base_range
        base = lo + (x + 1) / 2 * (hi - lo) + self.base_offset
        lo, hi = self.top_range
        top = lo + (y + 1) / 2 * (hi - lo)

        lim_lo, lim_hi = self.servo_limits
        base = max(lim_lo, min(lim_hi, base))
        top = max(lim_lo, min(lim_hi, top))
        return ServoAngles(round(base), round(top))

    def from_servo(self, base: float, top: float) -> tuple[float, float]:
        """Inverse of to_servo: real angles -> normalized (x, y)."""
        b_lo, b_hi = self.base_range
        t_lo, t_hi = self.top_range
        x = (base - self.base_offset - b_lo) / (b_hi - b_lo) * 2 - 1
        y = (top - t_lo) / (t_hi - t_lo) * 2 - 1
        if self.invert_base:
            x = -x
        if self.invert_top:
            y = -y
        return x, y
