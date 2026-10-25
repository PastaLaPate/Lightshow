import math
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import ClassVar

from lightshow.audio.data import AudioData
from lightshow.core.colors import hsv_to_rgb
from lightshow.devices.moving_head.commands import RGB, FadeCommand, FlickerCommand
from lightshow.devices.types import AbstractAnimation

COLOR_MODE = list[RGB] | Callable[[], RGB]

DEFAULT_RGBs: list[RGB] = RGB.fromRGBsList([[255, 0, 0], [0, 255, 0], [0, 0, 255]])

RAINBOW_KICK_COLORS = RGB.fromRGBsTupleList(
    [
        (148, 0, 211),  # Violet
        (75, 0, 130),  # Indigo
        (0, 0, 255),  # Blue
        (0, 255, 0),  # Green
        (255, 255, 0),  # Yellow
        (255, 127, 0),  # Orange
        (255, 0, 0),  # Red
    ]
)

BLUE_COLORS = RGB.fromRGBsTupleList(
    [
        (0, 0, 255),
        (0, 150, 255),
        (0, 0, 139),
        (20, 52, 164),
        (63, 0, 255),
        (93, 63, 211),
    ]
)

RED_COLORS = RGB.fromRGBsTupleList(
    [
        (136, 8, 8),
        (255, 0, 0),
        (215, 0, 64),
        (210, 4, 45),
        (139, 0, 0),
        (128, 0, 0),
        (99, 3, 48),
    ]
)


def random_rainbow_color():
    return RGB.fromList(
        [x * 255 for x in hsv_to_rgb(random.uniform(0, 1), 1, 1, 1)[:3]]
    )


class ColorTransformer(ABC):
    NAME: ClassVar[str]

    def __init_subclass__(cls, *, abstract: bool = False, **kw):
        super().__init_subclass__(**kw)
        if not abstract and not hasattr(cls, "NAME"):
            raise TypeError(f"{cls.__name__} must define Name")

    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def reactive() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def filter() -> Callable[[AbstractAnimation], bool]:
        pass

    @staticmethod
    @abstractmethod
    def override() -> bool:
        pass

    @abstractmethod
    def next(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FadeCommand | FlickerCommand:
        pass


class BlankTransformer(ColorTransformer):
    NAME = "Blank"

    @staticmethod
    def override():
        return False

    @staticmethod
    def reactive():
        return False

    @staticmethod
    def filter():
        return lambda _: True

    def next(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FadeCommand | FlickerCommand:
        return color


class LowsModulator(ColorTransformer):
    """Color mode that returns red with brightness modulated by low-frequency energy."""

    NAME = "Lows Modulator"

    MIN_BRIGHTNESS = 30
    MAX_BRIGHTNESS = 255

    ATTACK_TAU = 0.02  # how fast it rises on a hit
    RELEASE_TAU = 0.10  # how slowly it falls
    PEAK_HALF_LIFE = 1  # how fast the normalization peak decays

    def __init__(self, color: RGB | None = None):
        self.peak_energy = 1.0  # Avoid division by zero, self-calibrates upward
        self.level = 0.0
        self._last_t = time.monotonic()
        self._modulation_color = color or RGB(255, 0, 0)

    @staticmethod
    def override() -> bool:
        return True

    @staticmethod
    def reactive() -> bool:
        return True

    @staticmethod
    def filter() -> Callable[[AbstractAnimation], bool]:
        return lambda x: True

    def next(self, color, audio_data):
        now = time.monotonic()
        dt = min(now - self._last_t, 0.1)
        self._last_t = now

        try:
            lows = audio_data.get_ps_mean([0, 2])
            self.peak_energy = max(
                self.peak_energy * 0.5 ** (dt / self.PEAK_HALF_LIFE), lows, 1.0
            )
            target = min(lows / self.peak_energy, 1.0)
        except AttributeError, IndexError, ValueError:
            target = 1.0  # fallback: full brightness

        tau = self.ATTACK_TAU if target > self.level else self.RELEASE_TAU
        self.level += (target - self.level) * (1 - math.exp(-dt / tau))

        effective_brightness = self.MIN_BRIGHTNESS + self.level * (
            self.MAX_BRIGHTNESS - self.MIN_BRIGHTNESS
        )

        scale = effective_brightness / 255.0

        return RGB(
            int(self._modulation_color.r * scale),
            int(self._modulation_color.g * scale),
            int(self._modulation_color.b * scale),
        )


class RedLowsModulator(LowsModulator):
    NAME = "Red Modulator"

    def __init__(self):
        super().__init__(RGB(255, 0, 0))


class BlueLowsModulator(LowsModulator):
    NAME = "Blue Modulator"

    def __init__(self):
        super().__init__(RGB(0, 0, 255))


class PurpleLowsModulator(LowsModulator):
    NAME = "Purple Modulator"

    def __init__(self):
        super().__init__(RGB(130, 0, 255))


class ToBlackTransformer(ColorTransformer):
    NAME = "To black"

    @staticmethod
    def override():
        return False

    @staticmethod
    def reactive():
        return False

    @staticmethod
    def filter():
        return lambda _: True

    def next(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FadeCommand | FlickerCommand:
        return FadeCommand(color, RGB(0, 0, 0), 200)


class StartWhiteTransformer(ColorTransformer):
    NAME = "Start White"

    @staticmethod
    def override():
        return False

    @staticmethod
    def reactive():
        return False

    @staticmethod
    def filter():
        return lambda _: True

    def next(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FadeCommand | FlickerCommand:
        return FadeCommand(RGB(255, 255, 255), color, 100)


TRANSFORMERS = [
    BlankTransformer,
    RedLowsModulator,
    ToBlackTransformer,
    StartWhiteTransformer,
]
