import time
from typing import List, Callable, Tuple
from itertools import cycle
import numpy as np
import random

from lightshow.devices.animations import RGB
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    MHAnimationFrame,
    ServoCommand,
)


class CircleAnimation(AMHAnimation):
    def __init__(
        self,
        rgb: List[RGB] | Callable[[], RGB],
        speed=0.5,
        base_angle_offset=0,
    ):
        super().__init__()

        self.setRGB(rgb)

        self.change_color_on_tick = False
        self.last_color = RGB(255, 255, 255)

        self.tickeable = True
        self.progress_speed = speed

        self.baseAngleRange = (0, 120)
        self.topAngleRange = (0, 70)
        self.base_angle_offset = base_angle_offset

        self.boost_speed = 1.5
        self.boost_time = 0.3  # seconds
        self.boost_progress = 1
        # easeInOutQuart
        self.boost_curve = lambda t: 1 - t  # (
        #    8 * (t**4) if t < 0.5 else 1 - ((-2 * t + 2) ** 4) / 2
        # )

        self.circle_progress = 0
        self.color_cooldown = 0

    def setRGB(self, rgb: List[RGB] | Callable[[], RGB]):
        self.rgb = cycle(rgb) if isinstance(rgb, list) else rgb

    # dt in seconds
    # dt in seconds
    def next(self, isTick=False, dt=0.0) -> MHAnimationFrame:
        rgb = self.last_color

        # Handle tick-based color switching
        if not isTick:
            self.boost_progress = 0
            if random.uniform(0, 1) < 1 / 12:
                self.reverse()
            if not self.change_color_on_tick:
                rgb = self.nextRGB()
            self.last_color = rgb
            rgb = self.apply_transformer(rgb)
            self.color_cooldown = time.time_ns() + 0.2 * 1e9

        else:
            if self.change_color_on_tick and time.time_ns() >= self.color_cooldown:
                rgb = self.nextRGB()
                self.last_color = rgb

        # ---- BOOST HANDLING (now dt-based) ----
        if self.boost_progress < 1:
            # how much of the boost we progress this frame
            self.boost_progress += dt / self.boost_time
            if self.boost_progress > 1:
                self.boost_progress = 1

            # apply easing * dt
            self.circle_progress += (
                self.boost_curve(self.boost_progress) * self.boost_speed * dt
            )

        # ---- NORMAL MOVEMENT (dt-based) ----
        self.circle_progress += self.progress_speed * dt
        self.circle_progress %= 1

        # ---- ANGLES ----
        angle = self.circle_progress * 2 * np.pi
        if self.reversed:
            angle = -angle

        base, top = self.nextCurve(angle)

        return MHAnimationFrame(
            duration=0,
            rgb=rgb,
            topServo=ServoCommand(servo="top", angle=int(top)),
            baseServo=ServoCommand(
                servo="base", angle=int(base + self.base_angle_offset)
            ),
        )

    def nextCurve(self, t: float) -> Tuple[int, int]:
        base = (
            self.baseAngleRange[0]
            + self.baseAngleRange[1] / 2
            + self.baseAngleRange[1] / 2 * np.cos(t)
        )  # Max 0° to 90°
        top = (
            self.topAngleRange[0]
            + self.topAngleRange[1] / 2
            + self.topAngleRange[1] / 2 * np.sin(t)
        )  # Max 30 to 75
        return (base, top)

    def nextRGB(self) -> RGB:
        return next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()

    def reverse(self):
        super().reverse()
