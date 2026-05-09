from abc import abstractmethod
from typing import Literal, TypedDict, Union

from lightshow.audio.data import AudioData
from lightshow.devices.animations.AAnimation import (
    RGB,
    AAnimation,
    Command,
    FadeCommand,
    FlickerCommand,
)
from lightshow.devices.moving_head.moving_head_colors import (
    COLOR_MODE,
    ColorTransformer,
    DEFAULT_RGBs,
)


def QUART_OUT(t):
    return 1 - (1 - t) ** 4


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
    def __init__(self, angle: int):
        super().__init__("top", angle)


class MHAnimationFrame(TypedDict):
    duration: int  # Used to determine cooldown to add after
    rgb: Union[RGB, FlickerCommand, FadeCommand]
    topServo: ServoCommand
    baseServo: ServoCommand


class AMHAnimation(AAnimation):
    def __init__(self):
        super().__init__()
        self.transformer = None
        self.color_mode = DEFAULT_RGBs

    @abstractmethod
    def next(self, audio_data: AudioData, isTick=False, dt=0) -> MHAnimationFrame:
        pass

    def setTransformer(self, transformer: ColorTransformer):
        self.transformer = transformer

    def setRGB(self, color_mode: COLOR_MODE):
        self.color_mode = color_mode

    def apply_transformer(
        self, color: RGB, audio_data: AudioData
    ) -> RGB | FlickerCommand | FadeCommand:
        if self.transformer:
            transformed = self.transformer.next(color, audio_data)
            return transformed
        return color
