import random
from itertools import cycle

from lightshow.devices.animations.aanimation import RGB
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    BaseServoCommand,
    MHAnimationFrame,
    ServoCommand,
    TopServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE
from lightshow.devices.types import FixtureCalibration, ServoAngles


class ListAnimation(AMHAnimation):
    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: COLOR_MODE,
        points: list[tuple[float, float]],
        reverse_chance: float = 0.5,
    ):
        """
        Args:
            points: poses as (x, y) in normalized [-1, 1] space, where
                x is the base servo and y the top servo. One pose per beat.
            reverse_chance: probability of flipping direction after each
                full pass through the list.
        """
        super().__init__(calibration)
        if not points:
            raise ValueError("ListAnimation needs at least one point")

        self.setRGB(rgb)
        self.reverse_chance = reverse_chance

        self.poses: list[ServoAngles] = [calibration.to_servo(x, y) for x, y in points]
        self.index = -1  # first beat lands on pose 0
        self.steps_done = 0

        self.cached_rgb = RGB(0, 0, 0)
        self.cached_poses = (TopServoCommand(0), BaseServoCommand(0))

    @classmethod
    def from_servo_angles(
        cls,
        calibration: FixtureCalibration,
        rgb: COLOR_MODE,
        top: list[float],
        base: list[float],
        **kwargs,
    ) -> ListAnimation:
        """Port helper: build from real angles, like the old constructor."""
        points = [calibration.from_servo(b, t) for b, t in zip(base, top)]
        return cls(calibration, rgb, points, **kwargs)

    def setRGB(self, color_mode: COLOR_MODE):
        self.color_mode = color_mode
        self.rgb = cycle(color_mode) if isinstance(color_mode, list) else color_mode

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        if isTick:
            return MHAnimationFrame(
                duration=0,
                rgb=self.apply_transformer(self.cached_rgb, audio_data),
                topServo=self.cached_poses[0],
                baseServo=self.cached_poses[1],
            )

        # Advance one pose in the current direction
        direction = -1 if self.reversed else 1
        self.index = (self.index + direction) % len(self.poses)
        pose = self.poses[self.index]

        color: RGB = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
        self.cached_rgb = color
        self.cached_poses = (
            ServoCommand("top", angle=pose.top),
            ServoCommand("base", angle=pose.base),
        )

        # End of a full pass: maybe flip direction
        self.steps_done += 1
        if self.steps_done >= len(self.poses):
            self.steps_done = 0
            if random.random() < self.reverse_chance:
                self.reverse()

        return MHAnimationFrame(
            duration=0,
            rgb=self.apply_transformer(color, audio_data),
            topServo=self.cached_poses[0],
            baseServo=self.cached_poses[1],
        )

    def reverse(self):
        super().reverse()
