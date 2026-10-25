import random
import time
from collections.abc import Callable
from itertools import cycle

import numpy as np

from lightshow.devices.moving_head.commands import (
    RGB,
    BaseServoCommand,
    TopServoCommand,
)
from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    MHAnimationFrame,
)

# TODO: Redo this animations entirely


class CircleAnimation(AbstractMHAnimation):
    MAX_LAPS_PER_S = 2.0
    TEMPO_TIMEOUT = 2.5

    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: list[RGB] | Callable[[], RGB],
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
        phase: float = 0.0,
        laps_per_beat: float = 0.8,
        damping: float = 3.5,
        min_speed: float = 0.15,
        max_servo_speed: float = 600.0,
    ):
        """
        Args:
            scale: circle radius in normalized space (1.0 = full range).
            center: circle center in normalized space, (x=base, y=top).
            phase: starting offset as a fraction of a lap (0..1).
            laps_per_beat: how far each beat's kick coasts, in laps.
            damping: velocity decay rate (1/s). Higher = snappier, shorter coast.
            max_servo_speed: max servo angular speed in deg/s (clamps the kick).
        """
        super().__init__(calibration)

        self.setRGB(rgb)

        self.change_color_on_tick = False
        self.cached_color = RGB(0, 0, 0)
        self.color_cooldown = 0

        self.scale = scale
        self.center = center
        self.laps_per_beat = laps_per_beat
        self.damping = damping
        self.min_speed = min_speed
        self.max_servo_speed = max_servo_speed

        self.circle_progress = phase % 1  # laps, wrapped to 0..1
        self.speed = min_speed

        self._radius_deg = self._full_radius_deg() * scale

    def _full_radius_deg(self) -> float:
        b_lo, b_hi = self.calibration.base_range
        t_lo, t_hi = self.calibration.top_range
        return min(abs(b_hi - b_lo), abs(t_hi - t_lo)) / 2  # largest round circle

    def _kick_speed(self) -> float:
        """Speed so the coast above cruise covers ~laps_per_beat, clamped to the servos."""
        laps = self.laps_per_beat + random.uniform(-0.1, 0.1)
        v0 = self.min_speed + laps * self.damping
        v_max = self.max_servo_speed / (2 * np.pi * max(self._radius_deg, 1e-3))
        return min(v0, max(v_max, self.min_speed))

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        dt = min(dt, 0.1)

        if not isTick:  # beat
            # if random.random() < 1 / 12: Moved to controller
            #     self.reverse()
            self.speed = self._kick_speed()
            if not self.change_color_on_tick:
                self.cached_color = self.apply_transformer(self.nextRGB(), audio_data)
            self.color_cooldown = time.time_ns() + 0.2 * 1e9
        elif self.change_color_on_tick and time.time_ns() >= self.color_cooldown:
            self.cached_color = self.apply_transformer(self.nextRGB(), audio_data)

        if dt > 0:
            decay = np.exp(-self.damping * dt)
            excess = self.speed - self.min_speed
            dist = self.min_speed * dt + excess * (1 - decay) / self.damping
            direction = -1 if self.reversed else 1
            self.circle_progress = (self.circle_progress + direction * dist) % 1
            self.speed = self.min_speed + excess * decay

        x, y = self.nextCurve(self.circle_progress * 2 * np.pi)
        angles = self.calibration.to_servo(x, y)

        return MHAnimationFrame(
            duration=0,
            rgb=self.cached_color,
            topServo=TopServoCommand(angles.top),
            baseServo=BaseServoCommand(angles.base),
        )

    def shape(self, t: float) -> tuple[float, float]:
        """Unit shape, both axes in [-1, 1], same unit on both. Override per animation."""
        return (np.cos(t), np.sin(t))

    def nextCurve(self, t: float) -> tuple[float, float]:
        u, v = self.shape(t)
        b_lo, b_hi = self.calibration.base_range
        t_lo, t_hi = self.calibration.top_range
        rx = self._radius_deg / (abs(b_hi - b_lo) / 2)
        ry = self._radius_deg / (abs(t_hi - t_lo) / 2)
        cx, cy = self.center
        return (cx + rx * u, cy + ry * v)

    def setRGB(self, color_mode: list[RGB] | Callable[[], RGB]):
        self.color_mode = color_mode
        self.rgb = cycle(color_mode) if isinstance(color_mode, list) else color_mode

    def nextRGB(self) -> RGB:
        return next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()

    def reverse(self):
        super().reverse()
