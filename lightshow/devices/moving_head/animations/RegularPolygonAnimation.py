import math
import random
from itertools import cycle
from typing import List

from lightshow.devices.animations.AAnimation import RGB
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    BaseServoCommand,
    MHAnimationFrame,
    ServoCommand,
    TopServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE


class RegularPolygonAnimation(AMHAnimation):
    def __init__(
        self,
        rgb: COLOR_MODE,
        points_num=4,
        topRange=(0, 90),
        baseRange=(0, 90),
        angle_offset_cycle=15,
    ):
        super().__init__()
        self.setRGB(rgb)

        self.cached_rgb = RGB(0, 0, 0)
        self.cached_poses = (TopServoCommand(0), BaseServoCommand(0))

        self.cycle_progress = 0
        self.points_num = points_num

        self.baseRange = baseRange
        self.topRange = topRange
        self.angle_offset = 0
        self.angle_offset_cycle = angle_offset_cycle

        self.calculateServoPoses(self.angle_offset)

    def setRGB(self, color_mode: COLOR_MODE):
        self.rgb = cycle(color_mode) if isinstance(color_mode, list) else color_mode

    def next(self, audio_data, isTick=False, dt=0.0) -> MHAnimationFrame:
        if isTick:
            return (
                MHAnimationFrame(
                    duration=0,
                    rgb=self.apply_transformer(self.cached_rgb, audio_data),
                    topServo=self.cached_poses[0],
                    baseServo=self.cached_poses[1],
                )
                if self.transformer and self.transformer.reactive()
                else MHAnimationFrame(
                    duration=-1,
                    rgb=RGB(0, 0, 0),
                    topServo=TopServoCommand(0),
                    baseServo=BaseServoCommand(0),
                )
            )
        self.cycle_progress += 1
        if self.cycle_progress == min(
            len(self.topServoPositions), len(self.baseServoPositions)
        ):
            self.angle_offset += self.angle_offset_cycle
            if random.uniform(0, 1) < 1 / 2:
                self.reverse()
                self.cycle_progress = 0
            self.calculateServoPoses(self.angle_offset)
        color: RGB = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()  # ty:ignore[invalid-assignment]
        tcolor = self.apply_transformer(color, audio_data)
        self.cached_rgb = color
        self.cached_poses = (next(self.topServo), next(self.baseServo))
        return MHAnimationFrame(
            duration=0,
            rgb=tcolor,
            topServo=self.cached_poses[0],
            baseServo=self.cached_poses[1],
        )

    def calculateServoPoses(self, angle_offset=0):
        angle_step = 360 / self.points_num
        angle_step = math.radians(angle_step)
        self.topServoPositions: List[int] = [
            int(
                self.topRange[0]
                + (math.cos(angle_step * i + angle_offset) + 1)
                / 2
                * (self.topRange[1] - self.topRange[0])
            )
            for i in range(self.points_num)
        ]
        self.baseServoPositions: List[int] = [
            int(
                self.baseRange[0]
                + (math.sin(angle_step * i + angle_offset) + 1)
                / 2
                * (self.baseRange[1] - self.baseRange[0])
            )
            for i in range(self.points_num)
        ]

        self.topServo = cycle(
            [ServoCommand("top", angle=x) for x in self.topServoPositions]
        )
        self.baseServo = cycle(
            [ServoCommand("base", angle=x) for x in self.baseServoPositions]
        )

    def reverse(self):
        super().reverse()
        self.topServo = cycle(
            [ServoCommand("top", angle=x) for x in reversed(self.topServoPositions)]
            if not self.reversed
            else [ServoCommand("top", angle=x) for x in self.topServoPositions]
        )
        self.baseServo = cycle(
            [ServoCommand("base", angle=x) for x in reversed(self.baseServoPositions)]
            if not self.reversed
            else [ServoCommand("base", angle=x) for x in self.baseServoPositions]
        )

        next(self.topServo)
        next(self.baseServo)
