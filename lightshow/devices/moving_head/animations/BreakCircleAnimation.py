from lightshow.devices.animations.AAnimation import RGB
from lightshow.devices.moving_head.moving_head_animations import MHAnimationFrame
from lightshow.utils.colors import hsv_to_rgb
from .CircleAnimation import CircleAnimation


class BreakCircleAnimation(CircleAnimation):
    def __init__(self, base_angle_offset=0):
        super().__init__([RGB(255, 255, 255)], 0.35, base_angle_offset)
        self.change_color_on_tick = True
        self.hue = 0

    def next(self, isTick=True, dt=0.0) -> MHAnimationFrame:
        self.hue += 2 / 255
        self.hue %= 1
        return super().next(True, dt)

    def nextRGB(self):
        return RGB.fromList([x * 255 for x in hsv_to_rgb(self.hue, 1, 1, 1)[:3]])
