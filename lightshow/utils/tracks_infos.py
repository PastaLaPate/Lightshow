import asyncio
import threading
from typing import Callable, Any

# winrt is Windows-only. Try to import; if not available, provide safe fallbacks
try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager,
        GlobalSystemMediaTransportControlsSession,
        GlobalSystemMediaTransportControlsSessionMediaProperties,
        GlobalSystemMediaTransportControlsSessionPlaybackInfo,
    )
    WINRT_AVAILABLE = True
except Exception:
    WINRT_AVAILABLE = False
    GlobalSystemMediaTransportControlsSession = Any
    GlobalSystemMediaTransportControlsSessionMediaProperties = Any
    GlobalSystemMediaTransportControlsSessionPlaybackInfo = Any

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

# Only create the asyncio loop and thread when winrt is available
if WINRT_AVAILABLE:
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
else:
    loop = None


if WINRT_AVAILABLE:
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
else:
    # winrt not available - provide a lightweight no-op tracker so the rest of the app
    # can run on non-Windows platforms without errors.
    class TracksInfoTracker:

        def __init__(self):
            self.track_changed_listeners = []
            self.playback_status_changed_listeners = []

        def add_track_changed_listener(self, listener: TrackChangedListener):
            self.track_changed_listeners.append(listener)

        def add_playback_status_changed_listener(
            self, listener: PlaybackStatusChangedListener
        ):
            self.playback_status_changed_listeners.append(listener)
