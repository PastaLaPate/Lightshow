from lightshow.core.colors import hsv_to_rgb
from lightshow.devices.moving_head.commands import RGB
from lightshow.devices.moving_head.types import FixtureCalibration, MHAnimationFrame

from .circle_animation import CircleAnimation


class BreakCircleAnimation(CircleAnimation):
    def __init__(self, calibration: FixtureCalibration, hue_speed: float = 0.5):
        """hue_speed: full rainbow cycles per second (0.5 = one cycle every 2 s)."""
        super().__init__(calibration, rgb=[RGB(255, 255, 255)], speed=0.35)
        self.change_color_on_tick = True
        self.hue = 0.0
        self.hue_speed = hue_speed

    def next(self, audio_data, isTick=True, dt=0.0) -> MHAnimationFrame:
        self.hue = (self.hue + self.hue_speed * dt) % 1
        return super().next(audio_data, True, dt)

    def nextRGB(self):
        return RGB.fromList([x * 255 for x in hsv_to_rgb(self.hue, 1, 1, 1)[:3]])
