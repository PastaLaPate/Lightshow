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
    MAX_LAPS_PER_S = 2.0
    TEMPO_TIMEOUT = 2.5

    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: list[RGB] | Callable[[], RGB],
        speed: float = 0.5,
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
        phase: float = 0.0,
        lap_per_beat: bool = True,
        max_servo_speed: float = 270.0,
    ):
        """
        Args:
            speed: laps per second.
            scale: circle radius in normalized space (1.0 = full range).
            center: circle center in normalized space, (x=base, y=top).
            phase: starting offset as a fraction of a lap (0..1).
            lap_per_beat: do 1 lap each beat.
            max_servo_speed: max servo angular speed in deg/s
        """
        super().__init__(calibration)

        self.setRGB(rgb)

        self.change_color_on_tick = False
        self.cached_color = RGB(0, 0, 0)  # In case we move but don't change color

        self.progress_speed = speed
        self.scale = scale
        self.center = center
        self.lap_per_beat = lap_per_beat
        self.max_servo_speed = max_servo_speed

        self.circle_progress = phase % 1
        self.color_cooldown = 0

        self._last_beat_t: float | None = None
        self._beat_interval: float | None = None
        self._speed = speed
        self._radius_deg = self._full_radius_deg() * scale

    def _full_radius_deg(self) -> float:
        b_lo, b_hi = self.calibration.base_range
        t_lo, t_hi = self.calibration.top_range
        return min(abs(b_hi - b_lo), abs(t_hi - t_lo)) / 2  # largest round circle

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        dt = min(dt, 0.1)
        if not isTick:
            self._register_beat()
            if random.uniform(0, 1) < 1 / 12:
                self.reverse()
            if not self.change_color_on_tick:
                self.cached_color = self.apply_transformer(self.nextRGB(), audio_data)
            self.color_cooldown = time.time_ns() + 0.2 * 1e9
        elif self.change_color_on_tick and time.time_ns() >= self.color_cooldown:
            self.cached_color = self.apply_transformer(self.nextRGB(), audio_data)

        if (
            self._last_beat_t is not None
            and time.monotonic() - self._last_beat_t > self.TEMPO_TIMEOUT
        ):
            self._beat_interval = None

        if self.lap_per_beat and self._beat_interval:
            target_speed = 1.0 / self._beat_interval
            while target_speed > self.MAX_LAPS_PER_S:
                target_speed /= 2
        else:
            target_speed = self.progress_speed

        omega = 2 * np.pi * target_speed  # rad/s
        target_radius = min(
            self._full_radius_deg() * self.scale,
            self.max_servo_speed / omega,
        )

        k = 1 - np.exp(-dt / 0.15) if dt > 0 else 0.0
        self._speed += (target_speed - self._speed) * k
        self._radius_deg += (target_radius - self._radius_deg) * k

        direction = -1 if self.reversed else 1
        self.circle_progress = (self.circle_progress + direction * self._speed * dt) % 1

        x, y = self.nextCurve(self.circle_progress * 2 * np.pi)
        angles = self.calibration.to_servo(x, y)

        return MHAnimationFrame(
            duration=0,
            rgb=self.cached_color,
            topServo=ServoCommand(servo="top", angle=angles.top),
            baseServo=ServoCommand(servo="base", angle=angles.base),
        )

    def _register_beat(self):
        now = time.monotonic()
        if self._last_beat_t is not None:
            gap = now - self._last_beat_t
            if 0.25 < gap < 2.0:  # ignore double triggers and long pauses
                self._beat_interval = (
                    gap
                    if self._beat_interval is None
                    else 0.7 * self._beat_interval + 0.3 * gap
                )
        self._last_beat_t = now

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
