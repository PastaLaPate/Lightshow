import math
from itertools import cycle

from lightshow.devices.moving_head.colors import COLOR_MODE
from lightshow.devices.moving_head.commands import (
    RGB,
    BaseServoCommand,
    ServoCommand,
    TopServoCommand,
)
from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    MHAnimationFrame,
    ServoAngles,
)


class RegularPolygonAnimation(AbstractMHAnimation):
    def __init__(
        self,
        calibration: FixtureCalibration,
        rgb: COLOR_MODE,
        points_num: int = 4,
        angle_offset: float = 15,
        angle_offset_step: float = 0,
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
    ):
        """
        Args:
            points_num: number of polygon vertices.
            angle_offset: starting rotation of the polygon, in degrees.
            angle_offset_step: degrees added to the rotation after each full
                cycle (0 = the polygon never rotates).
            scale: polygon radius in normalized space (1.0 = full range).
            center: polygon center in normalized space, (x=base, y=top).
        """
        super().__init__(calibration)
        self.setRGB(rgb)

        self.points_num = points_num
        self.angle_offset = angle_offset
        self.angle_offset_step = angle_offset_step
        self.scale = scale
        self.center = center

        self.cached_rgb = RGB(0, 0, 0)
        self.cached_poses = (
            ServoCommand("top", angle=0),
            ServoCommand("base", angle=0),
        )

        self.poses: list[ServoAngles] = []
        self.index = -1  # first step lands on pose 0
        self.steps_done = 0

        self.calculateServoPoses()

    def setRGB(self, color_mode: COLOR_MODE):
        self.color_mode = color_mode
        self.rgb = cycle(color_mode) if isinstance(color_mode, list) else color_mode

    def calculateServoPoses(self):
        step = 2 * math.pi / self.points_num
        offset = math.radians(self.angle_offset)
        cx, cy = self.center

        self.poses = []
        for i in range(self.points_num):
            x = cx + self.scale * math.cos(offset + step * i)
            y = cy + self.scale * math.sin(offset + step * i)
            self.poses.append(self.calibration.to_servo(x, y))

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        if isTick:
            if self.transformer and self.transformer.reactive():
                return MHAnimationFrame(
                    duration=0,
                    rgb=self.apply_transformer(self.cached_rgb, audio_data),
                    topServo=self.cached_poses[0],
                    baseServo=self.cached_poses[1],
                )
            return MHAnimationFrame(
                duration=-1,
                rgb=RGB(0, 0, 0),
                topServo=TopServoCommand(0),
                baseServo=BaseServoCommand(0),
            )

        # Advance one vertex in the current direction
        direction = -1 if self.reversed else 1
        self.index = (self.index + direction) % len(self.poses)
        pose = self.poses[self.index]

        color: RGB = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
        self.cached_rgb = color
        self.cached_poses = (
            TopServoCommand(angle=pose.top),
            BaseServoCommand(angle=pose.base),
        )

        # End of a full lap:  optionally rotate the polygon
        self.steps_done += 1
        if self.steps_done >= len(self.poses):
            self.steps_done = 0
            # if random.random() < 0.5: Moved to controller
            #    self.reverse()
            if self.angle_offset_step:
                self.angle_offset += self.angle_offset_step
                self.calculateServoPoses()

        return MHAnimationFrame(
            duration=0,
            rgb=self.apply_transformer(color, audio_data),
            topServo=self.cached_poses[0],
            baseServo=self.cached_poses[1],
        )

    def reverse(self):
        super().reverse()
