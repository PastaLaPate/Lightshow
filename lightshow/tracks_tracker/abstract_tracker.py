from abc import ABC, abstractmethod

from lightshow.tracks_tracker.types import (
    PlaybackStatus,
    PlaybackStatusChangedListener,
    TrackChangedListener,
    TrackInfo,
)


class ATrackTracker(ABC):
    """Common interface shared across all platform implementations."""

    def __init__(self) -> None:
        self._track_changed_listeners: list[TrackChangedListener] = []
        self._playback_status_changed_listeners: list[
            PlaybackStatusChangedListener
        ] = []

    @abstractmethod
    def start(self) -> None:
        """Begin watching for media events."""

    def add_track_changed_listener(self, listener: TrackChangedListener) -> None:
        self._track_changed_listeners.append(listener)

    def add_playback_status_changed_listener(
        self, listener: PlaybackStatusChangedListener
    ) -> None:
        self._playback_status_changed_listeners.append(listener)

    def _notify_track_changed(self, player_name: str, info: TrackInfo) -> None:
        for listener in self._track_changed_listeners:
            listener(player_name, info)

    def _notify_playback_status_changed(
        self, player_name: str, status: PlaybackStatus
    ) -> None:
        for listener in self._playback_status_changed_listeners:
            listener(player_name, status)
