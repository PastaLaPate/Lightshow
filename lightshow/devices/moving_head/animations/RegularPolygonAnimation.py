from itertools import cycle
import math
import random

from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    MHAnimationFrame,
    ServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE


class RegularPolygonAnimation(AMHAnimation):
    def __init__(
        self, rgb: COLOR_MODE, points_num=4, topRange=(0, 90), baseRange=(0, 90), angle_offset_cycle=15
    ):
        super().__init__()
        self.tickeable = False
        self.points_num = points_num
        self.setRGB(rgb)
        self.cycle_progress = 0
        self.baseRange = baseRange
        self.topRange = topRange
        self.angle_offset = 0
        self.angle_offset_cycle = angle_offset_cycle
        self.calculateServoPoses(self.angle_offset)

    def setRGB(self, rgb: COLOR_MODE):
        self.rgb = cycle(rgb) if isinstance(rgb, list) else rgb

    def next(self, isTick=False) -> MHAnimationFrame:
        if isTick:
            raise NotImplementedError("PolygonAnimation shouldn't be ticked.")
        self.cycle_progress += 1
        if self.cycle_progress == min(
            len(self.topServoPositions), len(self.baseServoPositions)
        ):
            self.angle_offset += self.angle_offset_cycle
            if random.uniform(0, 1) < 1 / 2:
                self.reverse()
                self.cycle_progress = 0
            self.calculateServoPoses(self.angle_offset)
        color = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
        color = self.apply_transformer(color)
        return MHAnimationFrame(
            duration=0,
            rgb=color,
            topServo=next(self.topServo),
            baseServo=next(self.baseServo),
        )

    def calculateServoPoses(self, angle_offset=0):
        angle_step = 360 / self.points_num
        angle_step = math.radians(angle_step)
        self.topServoPositions = [
            self.topRange[0]
            + (math.cos(angle_step * i + angle_offset) + 1)
            / 2
            * (self.topRange[1] - self.topRange[0])
            for i in range(self.points_num)
        ]
        self.baseServoPositions = [
            self.baseRange[0]
            + (math.sin(angle_step * i + angle_offset) + 1)
            / 2
            * (self.baseRange[1] - self.baseRange[0])
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
            reversed(self.topServoPositions)
            if not self.reversed
            else self.topServoPositions
        )
        self.baseServo = cycle(
            reversed(self.baseServoPositions)
            if not self.reversed
            else self.baseServoPositions
        )

        next(self.topServo)
        next(self.baseServo)
