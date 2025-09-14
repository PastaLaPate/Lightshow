from abc import ABC, abstractmethod
from typing import Any, Tuple, List


class Command(ABC):
    @abstractmethod
    def toMHCommand(self) -> dict:
        pass


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


class AAnimation(ABC):
    def __init__(self):
        self.tickeable = False
        self.reversed = False

    @abstractmethod
    def next(self, isTick: bool = False) -> Any:
        pass

    def isTickeable(self) -> bool:
        return self.tickeable

    @abstractmethod
    def reverse(self):
        self.reversed = not self.reversed
