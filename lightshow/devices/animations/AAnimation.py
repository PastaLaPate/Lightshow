from abc import ABC, abstractmethod
from typing import Any, Tuple, List


class Command(ABC):
    @abstractmethod
    def toMHCommand(self) -> dict:
        pass

    @abstractmethod
    def toUDP_MH_Command(self) -> str:
        pass


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
    def fromTuple(cls, tuple: Tuple[int, int, int]):
        return cls.fromList(list(tuple))

    @classmethod
    def fromList(cls, list: List[int]):
        return cls(list[0], list[1], list[2])

    @classmethod
    def fromRGBsList(cls, list: List[List[int]]):
        return [cls.fromList(x) for x in list]

    @classmethod
    def fromRGBsTupleList(cls, list: List[Tuple[int, int, int]]):
        return [cls.fromTuple(x) for x in list]


class FlickerCommand(Command):
    color: RGB
    flicker: int  # Duration in milliseconds

    def __init__(self, rgb: RGB, flicker):
        self.color = rgb
        self.flicker = flicker

    def toMHCommand(self):
        return self.color.toMHCommand() | {"flicker": int(self.flicker)}

    def toUDP_MH_Command(self) -> str:
        return self.color.toUDP_MH_Command() + f";fl={int(self.flicker)}"


class FadeCommand(Command):
    from_: RGB
    to: RGB
    fade: int  # Duration in milliseconds

    def __init__(self, from_: RGB, to: RGB, fade: int):
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


class AAnimation(ABC):
    def __init__(self):
        self.tickeable = False
        self.reversed = False

    # dt: time since last frame in s
    @abstractmethod
    def next(self, isTick: bool = False, dt: float = 0) -> Any:
        pass

    def isTickeable(self) -> bool:
        return self.tickeable

    @abstractmethod
    def reverse(self):
        self.reversed = not self.reversed
