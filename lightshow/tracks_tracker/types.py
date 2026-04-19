from enum import IntEnum
from typing import Callable, Final


class PlaybackStatus(IntEnum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class TrackInfo:
    """Immutable, platform-agnostic track information."""

    __slots__ = ("title", "artist")

    def __init__(self, title: str = "", artist: str = "") -> None:
        self.title: Final[str] = title
        self.artist: Final[str] = artist

    def __repr__(self) -> str:
        return f"TrackInfo(title={self.title!r}, artist={self.artist!r})"


TrackChangedListener = Callable[[str, TrackInfo], None]
PlaybackStatusChangedListener = Callable[[str, PlaybackStatus], None]
