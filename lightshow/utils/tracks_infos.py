import asyncio
import logging
import os
import threading
from typing import Callable

# winrt is Windows-only. Try to import; if not available, provide safe fallbacks
if os.name == "nt":
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager,
        GlobalSystemMediaTransportControlsSession,
    )
    
if os.name == "posix":
    from dbus_next.aio.message_bus import MessageBus
    from dbus_next.constants import BusType
        
    from dbus_next.signature import Variant
    
MPRIS_PREFIX = "org.mpris.MediaPlayer2."
PLAYER_PRIORITY = [
    "org.mpris.MediaPlayer2.deezer",
    "org.mpris.MediaPlayer2.spotify",
    "org.mpris.MediaPlayer2.vlc",
    "org.mpris.MediaPlayer2.mpv",
    "org.mpris.MediaPlayer2.firefox",
    "org.mpris.MediaPlayer2.chromium",
]


# Common API classes that work across platforms
class TrackInfo:
    """Platform-agnostic track information."""
    def __init__(self, title: str = "", artist: str = ""):
        self.title = title
        self.artist = artist

class PlaybackInfo:
    """Platform-agnostic playback status."""
    def __init__(self, playback_status: str = "stopped"):
        self.playback_status = playback_status

# Session object for common API (represents a media player session)
class MediaSession:
    """Platform-agnostic media session object."""
    def __init__(self, name: str = ""):
        self.name = name

TrackChangedListener = Callable[
    [MediaSession, TrackInfo],
    None,
]

PlaybackStatusChangedListener = Callable[
    [MediaSession, PlaybackInfo],
    None,
]

# Event loop for async operations (used on both Windows and Linux)
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()


if os.name == "nt":
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

elif os.name == "posix":
    # Linux dbus implementation using MPRIS2 protocol
    class TracksInfoTracker:
        """Linux tracker using dbus and MPRIS2 for media player control."""

        def __init__(self):
            self.loop = loop
            self.bus = None

            self.players = {}          # name -> player iface
            self.props = {}            # name -> props iface
            self.status = {}           # name -> PlaybackStatus

            self.active_player = None

            self.track_changed_listeners = []
            self.playback_status_changed_listeners = []

            asyncio.run_coroutine_threadsafe(self._init(), loop)

        # ---------------- INIT ---------------- #

        async def _init(self):
            self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

            # Listen for player appear / disappear
            intro = await self.bus.introspect(
                "org.freedesktop.DBus", "/org/freedesktop/DBus"
            )
            obj = self.bus.get_proxy_object(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", intro
            )
            dbus_iface = obj.get_interface("org.freedesktop.DBus")
            dbus_iface.on_name_owner_changed(self._on_name_owner_changed)

            await self._scan_existing_players()

        async def _scan_existing_players(self):
            intro = await self.bus.introspect(
                "org.freedesktop.DBus", "/org/freedesktop/DBus"
            )
            obj = self.bus.get_proxy_object(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", intro
            )
            iface = obj.get_interface("org.freedesktop.DBus")
            names = await iface.call_list_names()

            for name in names:
                if name.startswith(MPRIS_PREFIX):
                    await self._attach_player(name)

        # ---------------- PLAYER MGMT ---------------- #

        async def _attach_player(self, name: str):
            if name in self.players:
                return

            try:
                intro = await self.bus.introspect(name, "/org/mpris/MediaPlayer2")
                obj = self.bus.get_proxy_object(name, "/org/mpris/MediaPlayer2", intro)

                player = obj.get_interface("org.mpris.MediaPlayer2.Player")
                props = obj.get_interface("org.freedesktop.DBus.Properties")

                props.on_properties_changed(
                    lambda iface, changed, invalid: self._on_properties_changed(
                        name, iface, changed
                    )
                )

                self.players[name] = player
                self.props[name] = props
                self.status[name] = await player.get_playback_status()

                self._reevaluate_active_player()
                await self._emit_track_info_force(name)

            except Exception:
                pass
            
        async def _emit_track_info_force(self, name):
            if name not in self.players:
                return

            player = self.players[name]
            meta = await player.get_metadata()

            title = meta.get("xesam:title", Variant("", "")).value
            artist = ""
            if "xesam:artist" in meta:
                artists = meta["xesam:artist"].value
                artist = artists[0] if artists else ""

            info = TrackInfo(title=title, artist=artist)

            for l in self.track_changed_listeners:
                l(name, info)


        def _detach_player(self, name: str):
            self.players.pop(name, None)
            self.props.pop(name, None)
            self.status.pop(name, None)

            if self.active_player == name:
                self.active_player = None
                self._reevaluate_active_player()

        # ---------------- SELECTION LOGIC ---------------- #

        def _reevaluate_active_player(self):
            playing = [n for n, s in self.status.items() if s == "Playing"]

            if not playing:
                return

            selected = self._pick_by_priority(playing)

            if selected != self.active_player:
                self.active_player = selected
                asyncio.run_coroutine_threadsafe(
                    self._emit_full_state(selected), self.loop
                )

        def _pick_by_priority(self, names):
            for p in PLAYER_PRIORITY:
                if p in names:
                    return p
            return names[0]

        # ---------------- SIGNAL HANDLERS ---------------- #

        def _on_name_owner_changed(self, name, old, new):
            if not name.startswith(MPRIS_PREFIX):
                return

            if new:
                asyncio.run_coroutine_threadsafe(
                    self._attach_player(name), self.loop
                )
            else:
                self._detach_player(name)

        def _on_properties_changed(self, name, iface, changed):
                if iface != "org.mpris.MediaPlayer2.Player":
                    return

                # 1. Handle Status Changes
                if "PlaybackStatus" in changed:
                    self.status[name] = changed["PlaybackStatus"].value
                    self._reevaluate_active_player()

                    if name == self.active_player:
                        self._emit_playback_status(name)

                # 2. Handle Metadata Changes
                # Fix: Check if Metadata is in 'changed' directly. 
                # We pass the 'changed' dict to _emit_track_info so we don't have to fetch it again.
                if "Metadata" in changed and name == self.active_player:
                    self._emit_track_info(name, metadata=changed["Metadata"])

        # ---------------- EMIT ---------------- #
        async def _emit_full_state(self, name):
            # When emitting full state, we don't have cached metadata from a signal,
            # so we pass None to force a fetch.
            self._emit_track_info(name, metadata=None)
            self._emit_playback_status(name)

        def _emit_track_info(self, name, metadata=None):
            """
            Emits track info. 
            If 'metadata' is provided (from a signal), uses it.
            Otherwise, fetches it from the player.
            """
            async def run():
                try:
                    # Use provided metadata or fetch it if missing
                    if metadata:
                        meta = metadata.value if isinstance(metadata, Variant) else metadata
                    else:
                        if name not in self.players:
                            return
                        player = self.players[name]
                        # SAFETY: await the get_metadata call
                        meta = await player.get_metadata()

                    # SAFETY: Handle cases where meta is None or keys are missing
                    if not meta:
                        return

                    # Extract Title
                    # dbus-next variants need careful handling. 
                    # meta is usually a dict of {str: Variant}
                    title_var = meta.get("xesam:title")
                    title = title_var.value if title_var else "Unknown Title"

                    # Extract Artist
                    artist = "Unknown Artist"
                    artist_var = meta.get("xesam:artist")
                    if artist_var:
                        # xesam:artist is usually a list of strings
                        artists = artist_var.value
                        if artists and isinstance(artists, list):
                            artist = artists[0]
                        elif isinstance(artists, str):
                            artist = artists

                    info = TrackInfo(title=title, artist=artist)

                    for l in self.track_changed_listeners:
                        l(name, info)

                except Exception as e:
                    # IMPORTANT: Catch errors in async tasks to see why it fails!
                    logging.getLogger("TracksInfoTracker").error(
                        f"Error emitting track info for {name}: {e}", exc_info=True
                    )

            asyncio.run_coroutine_threadsafe(run(), self.loop)


        def _emit_playback_status(self, name):
            raw = self.status.get(name)

            if raw == "Playing":
                status = PlaybackInfo("playing")
            elif raw == "Paused":
                status = PlaybackInfo("paused")
            else:
                status = PlaybackInfo("stopped")

            for l in self.playback_status_changed_listeners:
                l(name, status)



        # ---------------- API ---------------- #

        def add_track_changed_listener(self, listener):
            self.track_changed_listeners.append(listener)

        def add_playback_status_changed_listener(self, listener):
            self.playback_status_changed_listeners.append(listener)

else:
    # No platform support available - provide a lightweight no-op tracker
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
