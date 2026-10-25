from abc import abstractmethod
from dataclasses import dataclass
from typing import NamedTuple, Protocol, TypedDict, runtime_checkable

from lightshow.audio.data import AudioData
from lightshow.devices.moving_head.colors import (
    COLOR_MODE,
    ColorTransformer,
    DEFAULT_RGBs,
)
from lightshow.devices.moving_head.commands import (
    RGB,
    FadeCommand,
    FlickerCommand,
    ServoCommand,
)
from lightshow.devices.types import AbstractAnimation


class ServoAngles(NamedTuple):
    base: int
    top: int


def QUART_OUT(t):
    return 1 - (1 - t) ** 4


class MHAnimationFrame(TypedDict):
    duration: int  # Used to determine cooldown to add after
    rgb: RGB | FlickerCommand | FadeCommand
    topServo: ServoCommand
    baseServo: ServoCommand


class AbstractMHAnimation(AbstractAnimation):
    def __init__(self, calibration: FixtureCalibration):
        super().__init__()
        self.calibration = calibration
        self.transformer = None
        self.color_mode = DEFAULT_RGBs

    @abstractmethod
    def next(self, audio_data: AudioData, isTick=False, dt=0) -> MHAnimationFrame:
        pass

    def setTransformer(self, transformer: ColorTransformer):
        self.transformer = transformer

    def setRGB(self, color_mode: COLOR_MODE):
        self.color_mode = color_mode

    def apply_transformer(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FlickerCommand | FadeCommand:
        if self.transformer:
            transformed = self.transformer.next(color, audio_data)
            return transformed
        return color


@runtime_checkable
class HasPalette(Protocol):
    def setRGB(self, color_mode: COLOR_MODE) -> None: ...


@runtime_checkable
class ColorOnTick(Protocol):
    change_color_on_tick: bool


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
