import random
from abc import ABC, abstractmethod
from typing import Callable, List

from lightshow.audio.data import AudioData
from lightshow.devices.animations import AAnimation
from lightshow.devices.animations.AAnimation import RGB, FadeCommand, FlickerCommand
from lightshow.utils.colors import hsv_to_rgb

COLOR_MODE = List[RGB] | Callable[[], RGB]

DEFAULT_RGBs: List[RGB] = RGB.fromRGBsList([[255, 0, 0], [0, 255, 0], [0, 0, 255]])

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


def random_rainbow_color():
    return RGB.fromList(
        [x * 255 for x in hsv_to_rgb(random.uniform(0, 1), 1, 1, 1)[:3]]
    )


class ColorTransformer(ABC):
    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def reactive() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def filter() -> Callable[[AAnimation], bool]:
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


class RedLowsModulator(ColorTransformer):
    """Color mode that returns red with brightness modulated by low-frequency energy."""

    DECAY = 0.95  # Peak decays 5% per frame — tune this
    MIN_BRIGHTNESS = 50
    MAX_BRIGHTNESS = 255

    def __init__(self):
        self.peak_energy = 1.0  # Avoid division by zero, self-calibrates upward

    @staticmethod
    def override() -> bool:
        return True

    @staticmethod
    def reactive() -> bool:
        return True

    @staticmethod
    def filter() -> Callable[[AAnimation], bool]:
        from lightshow.devices.moving_head.animations.BounceAnimation import (
            BounceAnimation,
        )
        from lightshow.devices.moving_head.animations.CircleAnimation import (
            CircleAnimation,
        )

        return lambda x: isinstance(x, (CircleAnimation, BounceAnimation))

    def next(self, color, audio_data):
        brightness = self.MAX_BRIGHTNESS

        try:
            lows_energy = audio_data.get_ps_mean([0, 2])

            # Track peak with decay for dynamic normalization
            self.peak_energy = max(self.peak_energy * self.DECAY, lows_energy, 1.0)

            # Normalize to [0.0, 1.0] relative to recent peak
            normalized = min(lows_energy / self.peak_energy, 1.0)

            brightness = int(
                self.MIN_BRIGHTNESS
                + normalized * (self.MAX_BRIGHTNESS - self.MIN_BRIGHTNESS)
            )
        except AttributeError, IndexError, ValueError:
            pass

        return RGB(brightness, 0, 0)


class BlankTransformer(ColorTransformer):
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


class ToBlackTransformer(ColorTransformer):
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
    # BlankTransformer,
    RedLowsModulator,
    # ToBlackTransformer,
    # StartWhiteTransformer,
]
