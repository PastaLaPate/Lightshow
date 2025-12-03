from typing import Literal, TypedDict, Union

from lightshow.devices.animations.AAnimation import (
    Command,
    FadeCommand,
    FlickerCommand,
    AAnimation,
    RGB,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_TRANSFORMER

QUART_OUT = lambda t: 1 - (1 - t) ** 4

ServoType = Literal["base", "top"]


class ServoCommand(Command):
    servo: ServoType
    angle: int

    def __init__(self, servo: ServoType, angle: int):
        self.servo = servo
        self.angle = angle

    def toMHCommand(self):
        return {"servo": [{"servo": self.servo, "angle": self.angle}]}
    
    def toUDP_MH_Command(self) -> str:
        return ("tS" if self.servo == "top" else "bS") + f"={self.angle}"

class BaseServoCommand(ServoCommand):
    def __init__(self, angle: int):
        super().__init__("base", angle)


class TopServoCommand(ServoCommand):
    def __init__(self, angle):
        super().__init__("top", angle)


class MHAnimationFrame(TypedDict):
    duration: int  # Used to determine cooldown to add after
    rgb: Union[RGB, FlickerCommand, FadeCommand]
    topServo: ServoCommand
    baseServo: ServoCommand


class AMHAnimation(AAnimation):
    def next(self, isTick=False) -> MHAnimationFrame:
        pass

    def setTransformer(self, transformer: COLOR_TRANSFORMER):
        self.transformer = transformer

    def apply_transformer(self, color: RGB) -> RGB | FlickerCommand | FadeCommand:
        if self.transformer:
            return self.transformer(color)
        return color
