from itertools import cycle

from lightshow.devices.moving_head.colors import COLOR_MODE
from lightshow.devices.moving_head.commands import RGB
from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    MHAnimationFrame,
)


class LineAnimation(AbstractMHAnimation):
    NAME = "Line Animation"

    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: COLOR_MODE,
        angle: float = 0,
        length: float = 1,
    ):
        """Instantiates a LineAnimation

        Args:
            calibration (FixtureCalibration): the fixture's calibration.
            rgb (COLOR_MODE): the animation's current rgb mode.
            angle (float, optional): The line's angle in degree 0 corresponding to horizontal. Defaults to 0.
            length (float, optional): The line's length, mirrored on each side, 1 goes to max angle on each servo. Defaults to 1.
        """
        super().__init__(calibration)

        self.angle = angle
        self.length = length
        self.setRGB(rgb)

        self.cached_rgb = RGB(0, 0, 0)

        self.progress: float = 0

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
            TopServoCommand(angle=pose.top),
            BaseServoCommand(angle=pose.base),
        )

        return MHAnimationFrame(
            duration=0,
            rgb=self.apply_transformer(color, audio_data),
            topServo=self.cached_poses[0],
            baseServo=self.cached_poses[1],
        )
