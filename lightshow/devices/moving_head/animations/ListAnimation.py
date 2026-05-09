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


class ListAnimation(AMHAnimation):
    def __init__(
        self,
        rgb: COLOR_MODE,
        topServo: List[ServoCommand | int],
        baseServo: List[ServoCommand | int],
    ):
        super().__init__()
        self.cached_rgb = RGB(0, 0, 0)
        self.cached_poses = (TopServoCommand(0), BaseServoCommand(0))
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
        self.cycle_progress += 1
        if self.cycle_progress == min(
            len(self.topServoPositions), len(self.baseServoPositions)
        ):
            if random.uniform(0, 1) < 1 / 2:
                self.reverse()
                self.cycle_progress = 0
        color: RGB = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()  # ty:ignore[invalid-assignment]
        self.cached_rgb = color
        self.cached_poses = (next(self.topServo), next(self.baseServo))
        tcolor = self.apply_transformer(color, audio_data)
        return MHAnimationFrame(
            duration=0,
            rgb=tcolor,
            topServo=self.cached_poses[0],
            baseServo=self.cached_poses[1],
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
