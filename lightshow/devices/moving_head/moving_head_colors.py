import random
from typing import List, Callable

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


COLOR_TRANSFORMER = Callable[[RGB], FadeCommand | FlickerCommand]


def toFadeBlack(color: RGB) -> FadeCommand:
    return FadeCommand(color, RGB(0, 0, 0), 200)


def startFlicker(color: RGB) -> FadeCommand:
    return FadeCommand(RGB(255, 255, 255), color, 100)
