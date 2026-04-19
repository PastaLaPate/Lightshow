import os

if not os.name == "nt":
    raise ImportError("This module is only for Windows.")

import asyncio
import threading
from typing import Final

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSession,
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
)

from lightshow.tracks_tracker.abstract_tracker import ATrackTracker
from lightshow.tracks_tracker.types import PlaybackStatus, TrackInfo

_loop: Final[asyncio.AbstractEventLoop] = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


class WindowsTracksInfoTracker(ATrackTracker):
    """Windows tracker using the GlobalSystemMediaTransportControls API."""

    def __init__(self) -> None:
        super().__init__()
        self._manager: GlobalSystemMediaTransportControlsSessionManager | None = None

    def start(self) -> None:
        asyncio.run_coroutine_threadsafe(self._async_init(), _loop)

    async def _async_init(self) -> None:
        self._manager = (
            await GlobalSystemMediaTransportControlsSessionManager.request_async()
        )
        self._manager.add_current_session_changed(self._on_current_session_changed)
        session = self._manager.get_current_session()
        if session:
            session.add_playback_info_changed(self._on_playback_status_changed)
        await self._emit_track_info(session)
        self._on_playback_status_changed(session, None)

    def _on_current_session_changed(
        self,
        manager: GlobalSystemMediaTransportControlsSessionManager,
        _event: object,
    ) -> None:
        session = manager.get_current_session()
        if session:
            asyncio.run_coroutine_threadsafe(self._emit_track_info(session), _loop)
            session.add_playback_info_changed(self._on_playback_status_changed)

    async def _emit_track_info(
        self, session: GlobalSystemMediaTransportControlsSession
    ) -> None:
        props = await session.try_get_media_properties_async()
        if props:
            self._notify_track_changed(
                "", TrackInfo(title=props.title, artist=props.artist)
            )

    def _on_playback_status_changed(
        self,
        session: GlobalSystemMediaTransportControlsSession,
        _event: object | None,
    ) -> None:
        raw = session.get_playback_info()
        if raw:
            mapping = {
                GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING: PlaybackStatus.PLAYING,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED: PlaybackStatus.PAUSED,
                GlobalSystemMediaTransportControlsSessionPlaybackStatus.STOPPED: PlaybackStatus.STOPPED,
            }
            self._notify_playback_status_changed(
                "",
                mapping.get(raw.playback_status, PlaybackStatus.STOPPED),
            )
