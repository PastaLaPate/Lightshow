import asyncio
import threading
from typing import Callable
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSession,
    GlobalSystemMediaTransportControlsSessionMediaProperties,
    GlobalSystemMediaTransportControlsSessionPlaybackInfo,
)

TrackChangedListener = Callable[
    [
        GlobalSystemMediaTransportControlsSession,
        GlobalSystemMediaTransportControlsSessionMediaProperties,
    ],
    None,
]

PlaybackStatusChangedListener = Callable[
    [
        GlobalSystemMediaTransportControlsSession,
        GlobalSystemMediaTransportControlsSessionPlaybackInfo,
    ],
    None,
]


loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()


class TracksInfoTracker:

    def __init__(self):
        self.track_changed_listeners = []
        self.playback_status_changed_listeners = []
        self.manager = None
        # schedule initialization safely
        asyncio.run_coroutine_threadsafe(self.async_init(), loop)

    async def async_init(self):
        self.manager = (
            await GlobalSystemMediaTransportControlsSessionManager.request_async()
        )
        self.manager.add_current_session_changed(self.current_session_changed)
        session = self.manager.get_current_session()
        if session:
            session.add_playback_info_changed(self.playback_status_changed)

    def add_track_changed_listener(self, listener: TrackChangedListener):
        self.track_changed_listeners.append(listener)

    def add_playback_status_changed_listener(
        self, listener: PlaybackStatusChangedListener
    ):
        self.playback_status_changed_listeners.append(listener)

    def current_session_changed(
        self, manager: GlobalSystemMediaTransportControlsSessionManager, event
    ):
        session = manager.get_current_session()
        if session:
            asyncio.run_coroutine_threadsafe(
                self.async_current_session_changed(session, event),
                loop,
            )
            session.add_playback_info_changed(self.playback_status_changed)

    async def async_current_session_changed(
        self, session: GlobalSystemMediaTransportControlsSession, event
    ):
        infos = await session.try_get_media_properties_async()
        if infos:
            for listener in self.track_changed_listeners:
                listener(session, infos)

    def playback_status_changed(
        self, session: GlobalSystemMediaTransportControlsSession, event
    ):
        status = session.get_playback_info()
        if status:
            for listener in self.playback_status_changed_listeners:
                listener(session, status)
