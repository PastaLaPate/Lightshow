import random
import time
from collections.abc import Callable
from itertools import cycle

import numpy as np

from lightshow.devices.animations import RGB
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    MHAnimationFrame,
    ServoCommand,
)
from lightshow.devices.types import FixtureCalibration


class CircleAnimation(AMHAnimation):
    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: list[RGB] | Callable[[], RGB],
        speed: float = 0.5,
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
        phase: float = 0.0,
    ):
        """
        Args:
            speed: laps per second.
            scale: circle radius in normalized space (1.0 = full range).
            center: circle center in normalized space, (x=base, y=top).
            phase: starting offset as a fraction of a lap (0..1).
        """
        super().__init__(calibration)

        self.setRGB(rgb)

        self.change_color_on_tick = False
        self.cached_color = RGB(0, 0, 0)  # In case we move but don't change color

        self.progress_speed = speed
        self.scale = scale
        self.center = center

        self.boost_speed = 2
        self.boost_time = 0.4  # seconds
        self.boost_progress = 1
        self.boost_curve = lambda t: 1 - t

        self.circle_progress = phase % 1
        self.color_cooldown = 0

    def setRGB(self, color_mode: list[RGB] | Callable[[], RGB]):
        self.color_mode = color_mode
        self.rgb = cycle(color_mode) if isinstance(color_mode, list) else color_mode

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        if not isTick:
            self.boost_progress = 0
            if random.uniform(0, 1) < 1 / 12:
                self.reverse()
            if not self.change_color_on_tick:
                rgb = self.nextRGB()
                rgb = self.apply_transformer(rgb, audio_data)
                self.cached_color = rgb

            self.color_cooldown = time.time_ns() + 0.2 * 1e9

        else:
            if self.change_color_on_tick and time.time_ns() >= self.color_cooldown:
                rgb = self.nextRGB()
                rgb = self.apply_transformer(rgb, audio_data)
                self.cached_color = rgb

        velocity = self.progress_speed
        if self.boost_progress < 1:
            self.boost_progress = min(self.boost_progress + dt / self.boost_time, 1)
            velocity += self.boost_curve(self.boost_progress) * self.boost_speed

        direction = -1 if self.reversed else 1
        self.circle_progress = (self.circle_progress + direction * velocity * dt) % 1

        x, y = self.nextCurve(self.circle_progress * 2 * np.pi)
        angles = self.calibration.to_servo(x, y)

        return MHAnimationFrame(
            duration=0,
            rgb=self.cached_color,
            topServo=ServoCommand(servo="top", angle=angles.top),
            baseServo=ServoCommand(servo="base", angle=angles.base),
        )

    def nextCurve(self, t: float) -> tuple[float, float]:
        cx, cy = self.center
        return (cx + self.scale * np.cos(t), cy + self.scale * np.sin(t))

    def nextRGB(self) -> RGB:
        return next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()

    def reverse(self):
        super().reverse()
