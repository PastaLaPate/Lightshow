from itertools import cycle
from lightshow.devices.animations.AAnimation import RGB
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    BaseServoCommand,
    MHAnimationFrame,
    TopServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE


class BounceAnimation(AMHAnimation):
    NAME = "Bounce"

    def __init__(self, rgb: COLOR_MODE):
        super().__init__()

        self.tickeable = True
        self.setRGB(rgb)
        self.cycle_progress = 0
        self.direction = 1  # 1 for forward, -1 for backward
        self.velocity = 0
        self.base_range = (0, 120)
        self.top_range = (0, 50)
        self.y_f = lambda x: 0.5 + 3 * (
            0.45 * x - 0.45 * x**2
        )  # Sketchy parabola function

        self.color = RGB(255, 255, 255)

    def setRGB(self, rgb: COLOR_MODE):
        self.rgb = cycle(rgb) if isinstance(rgb, list) else rgb

    def next(self, isTick=False) -> MHAnimationFrame:
        if isTick:
            self.velocity -= self.velocity * 0.05  # gradual deceleration
            self.cycle_progress += self.direction / 100 + self.velocity * self.direction
            if self.cycle_progress >= 1:
                self.direction = -1
                self.cycle_progress = 1
            elif self.cycle_progress <= 0:
                self.direction = 1
                self.cycle_progress = 0
        else:
            # Means beat
            self.velocity = 0.04
            color = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
            self.color = self.apply_transformer(color)

        base_angle = int(
            (self.base_range[1] - self.base_range[0]) * self.cycle_progress
            + self.base_range[0]
        )  # Basic linear interpolation
        top_angle = int(
            (self.top_range[1] - self.top_range[0]) * self.y_f(self.cycle_progress)
            + self.top_range[0]
        )  # Parabolic interpolation
        return MHAnimationFrame(
            duration=0,
            rgb=self.color,
            topServo=TopServoCommand(top_angle),
            baseServo=BaseServoCommand(base_angle),
        )

    def reverse(self):
        return super().reverse()
