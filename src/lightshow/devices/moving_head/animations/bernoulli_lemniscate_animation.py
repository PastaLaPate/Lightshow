from collections.abc import Callable

import numpy as np

from lightshow.devices.animations import RGB
from lightshow.devices.moving_head.animations.circle_animation import (
    CircleAnimation,
)
from lightshow.devices.types import FixtureCalibration

_LEMNISCATE_MAX_Y = np.sqrt(2) / 4


class BernoulliLemniscateAnimation(CircleAnimation):
    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: list[RGB] | Callable[[], RGB],
        speed: float = 0.5,
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
        phase: float = 0.0,
        fill_y: bool = True,
    ):
        """
        Args:
            speed: laps per second.
            scale: overall size in normalized space (1.0 = full range on x).
            center: center of the figure-eight, (x=base, y=top).
            phase: starting offset as a fraction of a lap (0..1).
            fill_y: if True, stretch the curve so it also spans the full
                y range (a fatter figure-eight). If False, keep the true
                lemniscate proportions (about 1 : 0.35), which looks flatter
                but is geometrically correct.
        """
        super().__init__(calibration, rgb, speed, scale, center, phase)
        self.fill_y = fill_y

    def nextCurve(self, t: float) -> tuple[float, float]:
        """
        Lemniscate of Bernoulli (a = 1), returned in normalized space:
            x(t) = cos(t) / (1 + sin^2(t))                 in [-1, 1]
            y(t) = sin(t) * cos(t) / (1 + sin^2(t))        in [-sqrt(2)/4, sqrt(2)/4]
        """
        denom = 1 + np.sin(t) ** 2
        x = np.cos(t) / denom
        y = (np.sin(t) * np.cos(t)) / denom

        if self.fill_y:
            y = y / _LEMNISCATE_MAX_Y  # -> [-1, 1]

        cx, cy = self.center
        return (cx + self.scale * x, cy + self.scale * y)
