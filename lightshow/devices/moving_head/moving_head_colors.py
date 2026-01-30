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


class RedLowsModulator:
    """Color mode that returns red with brightness modulated by low-frequency energy."""
    
    def __init__(self):
        self.last_audio_data = None
        self.min_brightness = 50  # Minimum brightness for red (0-255)
        self.max_brightness = 255  # Maximum brightness for red
    
    def set_audio_data(self, audio_data):
        """Update audio data for modulation."""
        self.last_audio_data = audio_data
    
    def __call__(self):
        """Return red color with brightness modulated by lows energy."""
        brightness = self.max_brightness  # Default to full brightness
        
        if self.last_audio_data is not None:
            # Get low-frequency energy from first few FFT bins (typically 0-4 represent lows)
            try:
                lows_energy = self.last_audio_data.get_ps_mean([0, 4])
                # Normalize energy to 0-1 range (assuming typical values are 0-1, adjust if needed)
                normalized_energy = min(max(lows_energy, 0), 1)
                # Map energy to brightness range
                brightness = int(self.min_brightness + normalized_energy * (self.max_brightness - self.min_brightness))
            except (AttributeError, IndexError, ValueError):
                pass  # If audio data is invalid, use default brightness
        
        return RGB(brightness, 0, 0)


COLOR_TRANSFORMER = Callable[[RGB], RGB | FadeCommand | FlickerCommand]


def nothingTransformer(color: RGB) -> RGB:
    return color


def toFadeBlack(color: RGB) -> FadeCommand:
    return FadeCommand(color, RGB(0, 0, 0), 200)


def startFlicker(color: RGB) -> FadeCommand:
    return FadeCommand(RGB(255, 255, 255), color, 100)
