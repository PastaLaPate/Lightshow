from typing import List
from itertools import cycle
import random

from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    MHAnimationFrame,
    ServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE


class ListAnimation(AMHAnimation):
    def __init__(
        self,
        rgb: COLOR_MODE,
        topServo: List[ServoCommand | int],
        baseServo: List[ServoCommand | int],
    ):
        super().__init__()
        self.tickeable = False
        self.setRGB(rgb)
        self.topServoPositions = [
            x if isinstance(x, ServoCommand) else ServoCommand("top", angle=x)
            for x in topServo
        ]
        self.topServo = cycle(self.topServoPositions)
        self.baseServoPositions = [
            x if isinstance(x, ServoCommand) else ServoCommand("base", angle=x)
            for x in baseServo
        ]
        self.baseServo = cycle(self.baseServoPositions)
        self.cycle_progress = 0

    def setRGB(self, rgb: COLOR_MODE):
        self.rgb = cycle(rgb) if isinstance(rgb, list) else rgb

    def next(self, isTick=False, dt=0.0) -> MHAnimationFrame:
        if isTick:
            raise NotImplementedError("ListAnimation shouldn't be ticked.")
        self.cycle_progress += 1
        if self.cycle_progress == min(
            len(self.topServoPositions), len(self.baseServoPositions)
        ):
            if random.uniform(0, 1) < 1 / 2:
                self.reverse()
                self.cycle_progress = 0
        color = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
        color = self.apply_transformer(color)
        return MHAnimationFrame(
            duration=0,
            rgb=color,
            topServo=next(self.topServo),
            baseServo=next(self.baseServo),
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
