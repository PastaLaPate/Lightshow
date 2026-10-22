from collections.abc import Callable
from itertools import cycle

from lightshow.devices.animations.aanimation import RGB, FadeCommand
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    BaseServoCommand,
    MHAnimationFrame,
    TopServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE
from lightshow.devices.types import FixtureCalibration


class BounceAnimation(AMHAnimation):
    NAME = "Bounce"

    def __init__(self, calibration: FixtureCalibration, rgb: COLOR_MODE):
        super().__init__(calibration)

        self.tickeable = True
        self.setRGB(rgb)

        self.cycle_progress = 0.0  # 0 -> left, 1 -> right
        self.direction = 1  # 1 forward, -1 backward
        self.velocity = 0.0  # progress units per second

        # Cross from one side to the other in X seconds
        self.target_cross_time = 0.2  # seconds

        # Arc height as a function of progress, in 0..1 (0 = bottom of the
        # top range, 1 = top). Peaks at the middle, lower at the sides.
        self.y_f = lambda x: 0.7 - 2 * (x - 0.5) ** 2
        self.color = RGB(255, 255, 255)

    def setRGB(self, color_mode: COLOR_MODE):
        self.color_mode = color_mode
        self.rgb: cycle[RGB] | Callable[[], RGB] = (
            cycle(color_mode) if isinstance(color_mode, list) else color_mode
        )

    def _compute_required_velocity(self, dt_est: float = 1 / 60):
        distance = (
            (1.0 - self.cycle_progress) if self.direction == 1 else self.cycle_progress
        )
        if distance <= 0:
            return 0.01

        T = self.target_cross_time
        d = 3.0  # damping strength
        dt = dt_est

        # Discrete damping factor per frame
        r = 1.0 - d * dt
        if r <= 0:
            return distance / T

        N = int(T / dt)
        denom = 1.0 - r**N
        if denom < 1e-6:
            return distance / T

        v0 = distance * d / denom
        return v0 * 1.05  # small boost

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        self.velocity *= max(0, 1.0 - 3.0 * dt)  # damping, proportional to dt

        if isTick:
            self.cycle_progress += self.direction * self.velocity * dt

            # Clamp & bounce
            if self.cycle_progress >= 1.0:
                self.cycle_progress = 1.0
                self.direction = -1
            elif self.cycle_progress <= 0.0:
                self.cycle_progress = 0.0
                self.direction = 1
        else:
            # Beat: reverse if we're near the middle, then kick toward the far side
            if self.velocity > 0.01 and 0.4 < self.cycle_progress < 0.6:
                self.direction *= -1
            v = self._compute_required_velocity(dt if dt > 0 else 1 / 60)
            self.velocity = max(v, 0.2)

        # Update color
        color: RGB = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
        self.color = self.apply_transformer(color, audio_data)

        # Progress 0..1 -> normalized -1..1 -> servo angles
        x = 2.0 * self.cycle_progress - 1.0
        y = 2.0 * self.y_f(self.cycle_progress) - 1.0
        angles = self.calibration.to_servo(x, y)

        # FadeCommand support
        if isinstance(self.color, FadeCommand) and isTick:
            self.color = (
                self.color.to
                if (self.color.to.r or self.color.to.g or self.color.to.b)
                else self.color.from_
            )

        return MHAnimationFrame(
            duration=0,
            rgb=self.color,
            topServo=TopServoCommand(angles.top),
            baseServo=BaseServoCommand(angles.base),
        )

    def reverse(self):
        # Cannot reverse this effect
        pass
