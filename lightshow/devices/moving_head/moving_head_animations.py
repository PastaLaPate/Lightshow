from abc import abstractmethod
from typing import Literal, TypedDict, Union

from devices.animations.AAnimation import (
    Command,
    FadeCommand,
    FlickerCommand,
    AAnimation,
    RGB,
)

QUART_OUT = lambda t: 1 - (1 - t) ** 4

ServoType = Literal["base", "top"]


class ServoCommand(Command):
    servo: ServoType
    angle: int

    def __init__(self, servo: ServoType, angle: int):
        self.servo = servo
        self.angle = angle

    def toMHCommand(self):
        return {"servo": self.servo, "angle": self.angle}


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
    @abstractmethod
    def next(self, isTick=False) -> MHAnimationFrame:
        pass
