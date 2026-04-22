import random
from typing import Callable, List

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


class RedLowsModulator:
    """Color mode that returns red with brightness modulated by low-frequency energy."""

    DECAY = 0.95  # Peak decays 5% per frame — tune this
    MIN_BRIGHTNESS = 50
    MAX_BRIGHTNESS = 255

    def __init__(self):
        self.last_audio_data = None
        self.peak_energy = 1.0  # Avoid division by zero, self-calibrates upward

    def set_audio_data(self, audio_data):
        self.last_audio_data = audio_data

    def __call__(self):
        brightness = self.MAX_BRIGHTNESS

        if self.last_audio_data is not None:
            try:
                lows_energy = self.last_audio_data.get_ps_mean([0, 2])

                # Track peak with decay for dynamic normalization
                self.peak_energy = max(self.peak_energy * self.DECAY, lows_energy, 1.0)

                # Normalize to [0.0, 1.0] relative to recent peak
                normalized = min(lows_energy / self.peak_energy, 1.0)

                brightness = int(
                    self.MIN_BRIGHTNESS
                    + normalized * (self.MAX_BRIGHTNESS - self.MIN_BRIGHTNESS)
                )
            except (AttributeError, IndexError, ValueError):
                pass

        return RGB(brightness, 0, 0)


COLOR_TRANSFORMER = Callable[[RGB], RGB | FadeCommand | FlickerCommand]


def nothingTransformer(color: RGB) -> RGB:
    return color


def toFadeBlack(color: RGB) -> FadeCommand:
    return FadeCommand(color, RGB(0, 0, 0), 200)


def startFlicker(color: RGB) -> FadeCommand:
    return FadeCommand(RGB(255, 255, 255), color, 100)
