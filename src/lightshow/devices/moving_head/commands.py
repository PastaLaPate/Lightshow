from __future__ import annotations

from abc import ABC, abstractmethod

from lightshow.devices.moving_head.types import ServoType


class Command(ABC):
    @abstractmethod
    def toMHCommand(self) -> dict:
        pass

    @abstractmethod
    def toUDP_MH_Command(self) -> str:
        pass


# TODO: remove like toMH and rename like to serialize...

"""

UDP Packet Structure:

number (32 bits) : Packet ID
args (in format key=value separated by ;) : Arguments

Arguments:
Servos:
- bS : Base Servo Angle
- tS : Top Servo Angle
Base RGB:
- r : LED Red Value (0-255)
- g : LED Green Value (0-255)
- b : LED Blue Value (0-255)

Flicker:
- fl : Flicker Duration (ms)

Fade:
- fa : Fade Duration (ms)
- fr : From Red Value (0-255)
- fg : From Green Value (0-255)
- fb : From Blue Value (0-255)

"""


class RGB(Command):  # out of 255
    r: int
    g: int
    b: int

    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    def rgbDict(self):
        return {"r": int(self.r), "g": int(self.g), "b": int(self.b)}

    def toMHCommand(self):
        return {"led": self.rgbDict()}

    def toUDP_MH_Command(self) -> str:
        return f"r={self.r};g={self.g};b={self.b}"

    @classmethod
    def fromTuple(cls, tuple: tuple[int, int, int]) -> RGB:
        return cls.fromList(list(tuple))

    @classmethod
    def fromList(cls, list: list[int]) -> RGB:
        return cls(list[0], list[1], list[2])

    @classmethod
    def fromRGBsList(cls, list: list[list[int]]) -> list[RGB]:
        return [cls.fromList(x) for x in list]

    @classmethod
    def fromRGBsTupleList(cls, list: list[tuple[int, int, int]]) -> list[RGB]:
        return [cls.fromTuple(x) for x in list]


class FlickerCommand(Command):
    color: RGB
    flicker: int

    def __init__(self, rgb: RGB, flicker: int):
        """Creates a FlickerCommand

        Args:
            rgb (RGB): color of the flicker.
            flicker (int): duration in ms of the flicker.
        """
        self.color = rgb
        self.flicker = flicker

    def toMHCommand(self):
        return self.color.toMHCommand() | {"flicker": int(self.flicker)}

    def toUDP_MH_Command(self) -> str:
        return self.color.toUDP_MH_Command() + f";fl={int(self.flicker)}"


class FadeCommand(Command):
    from_: RGB
    to: RGB
    fade: int

    def __init__(self, from_: RGB, to: RGB, fade: int):
        """Creates a FadeCommand.

        Args:
            from_ (RGB): color to fade from.
            to (RGB): color to fade to.
            fade (int): fade's duration in ms.
        """
        self.from_ = from_
        self.to = to
        self.fade = fade

    def toMHCommand(self):
        return self.to.toMHCommand() | {"from": self.from_.rgbDict(), "fade": self.fade}

    def toUDP_MH_Command(self) -> str:
        return (
            self.to.toUDP_MH_Command()
            + f";fa={int(self.fade)};fr={self.from_.r};fg={self.from_.g};fb={self.from_.b}"
        )


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
