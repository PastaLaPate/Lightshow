import asyncio
import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Callable, Final

# ─── winrt (Windows-only) ────────────────────────────────────────────────────

if os.name == "nt":
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSession,
        GlobalSystemMediaTransportControlsSessionManager,
    )

# ─── dbus (Linux-only) ───────────────────────────────────────────────────────

if os.name == "posix":
    from typing import Protocol, runtime_checkable

    from dbus_next.aio.message_bus import MessageBus
    from dbus_next.constants import BusType
    from dbus_next.signature import Variant

    @runtime_checkable
    class DBusInterface(Protocol):
        def on_name_owner_changed(
            self,
            callback: Callable[[str, str, str], None],
        ) -> None: ...

        async def call_list_names(self) -> list[str]: ...

    @runtime_checkable
    class PropertiesInterface(Protocol):
        def on_properties_changed(
            self,
            callback: Callable[[str, dict[str, Variant], list[str]], None],
        ) -> None: ...

    @runtime_checkable
    class PlayerInterface(Protocol):
        async def get_playback_status(self) -> str: ...
        async def get_metadata(self) -> dict[str, Variant]: ...


# ─── Constants ───────────────────────────────────────────────────────────────

MPRIS_PREFIX: Final = "org.mpris.MediaPlayer2."

PLAYER_PRIORITY: Final[list[str]] = [
    "org.mpris.MediaPlayer2.deezer",
    "org.mpris.MediaPlayer2.spotify",
    "org.mpris.MediaPlayer2.vlc",
    "org.mpris.MediaPlayer2.mpv",
    "org.mpris.MediaPlayer2.firefox",
    "org.mpris.MediaPlayer2.chromium",
]

# ─── Platform-agnostic data classes ──────────────────────────────────────────


class TrackInfo:
    """Immutable, platform-agnostic track information."""

    __slots__ = ("title", "artist")

    def __init__(self, title: str = "", artist: str = "") -> None:
        self.title: Final[str] = title
        self.artist: Final[str] = artist

    def __repr__(self) -> str:
        return f"TrackInfo(title={self.title!r}, artist={self.artist!r})"


class PlaybackInfo:
    """Immutable, platform-agnostic playback status."""

    __slots__ = ("playback_status",)

    VALID_STATUSES: Final[frozenset[str]] = frozenset({"playing", "paused", "stopped"})

    def __init__(self, playback_status: str = "stopped") -> None:
        if playback_status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid playback_status {playback_status!r}. "
                f"Must be one of {self.VALID_STATUSES}."
            )
        self.playback_status: Final[str] = playback_status

    def __repr__(self) -> str:
        return f"PlaybackInfo(playback_status={self.playback_status!r})"


# ─── Listener type aliases ────────────────────────────────────────────────────

TrackChangedListener = Callable[[str, TrackInfo], None]
PlaybackStatusChangedListener = Callable[[str, PlaybackInfo], None]

# ─── Shared event loop ───────────────────────────────────────────────────────

_loop: Final[asyncio.AbstractEventLoop] = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()

# ─── Abstract base ────────────────────────────────────────────────────────────


class BaseTracksInfoTracker(ABC):
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
        self, player_name: str, status: PlaybackInfo
    ) -> None:
        for listener in self._playback_status_changed_listeners:
            listener(player_name, status)


# ─── Windows implementation ──────────────────────────────────────────────────

if os.name == "nt":

    class TracksInfoTracker(BaseTracksInfoTracker):
        """Windows tracker using the GlobalSystemMediaTransportControls API."""

        def __init__(self) -> None:
            super().__init__()
            self._manager: GlobalSystemMediaTransportControlsSessionManager | None = (
                None
            )

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
            _event: object,
        ) -> None:
            raw = session.get_playback_info()
            if raw:
                self._notify_playback_status_changed(
                    "", PlaybackInfo(playback_status=str(raw.playback_status).lower())
                )

# ─── Linux / MPRIS2 implementation ───────────────────────────────────────────

elif os.name == "posix":
    _log = logging.getLogger("TracksInfoTracker")

    def _extract_title(meta: "dict[str, Variant]") -> str:
        title_var = meta.get("xesam:title")
        if title_var is None:
            return "Unknown Title"
        value = title_var.value
        return value if isinstance(value, str) else "Unknown Title"

    def _extract_artist(meta: "dict[str, Variant]") -> str:
        artist_var = meta.get("xesam:artist")
        if artist_var is None:
            return "Unknown Artist"
        value = artist_var.value
        if isinstance(value, list) and value:
            first = value[0]
            return first if isinstance(first, str) else "Unknown Artist"
        if isinstance(value, str):
            return value
        return "Unknown Artist"

    def _playback_status_from_mpris(raw: str) -> PlaybackInfo:
        mapping: dict[str, str] = {
            "Playing": "playing",
            "Paused": "paused",
            "Stopped": "stopped",
        }
        return PlaybackInfo(mapping.get(raw, "stopped"))

    class TracksInfoTracker(BaseTracksInfoTracker):
        """Linux tracker using dbus/MPRIS2."""

        def __init__(self) -> None:
            super().__init__()
            self._bus: "MessageBus | None" = None
            self._players: "dict[str, PlayerInterface]" = {}
            self._props: "dict[str, PropertiesInterface]" = {}
            self._status: dict[str, str] = {}
            self._active_player: str | None = None

        def start(self) -> None:
            asyncio.run_coroutine_threadsafe(self._init(), _loop)

        # ── Init ──────────────────────────────────────────────────────────────

        async def _init(self) -> None:
            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()

            intro = await self._bus.introspect(
                "org.freedesktop.DBus", "/org/freedesktop/DBus"
            )
            obj = self._bus.get_proxy_object(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", intro
            )
            dbus_iface = obj.get_interface("org.freedesktop.DBus")
            if not isinstance(dbus_iface, DBusInterface):
                raise RuntimeError("org.freedesktop.DBus interface not available.")

            dbus_iface.on_name_owner_changed(self._on_name_owner_changed)
            await self._scan_existing_players()

        async def _scan_existing_players(self) -> None:
            if not self._bus:
                return

            intro = await self._bus.introspect(
                "org.freedesktop.DBus", "/org/freedesktop/DBus"
            )
            obj = self._bus.get_proxy_object(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", intro
            )
            iface = obj.get_interface("org.freedesktop.DBus")
            if not isinstance(iface, DBusInterface):
                return

            names: list[str] = await iface.call_list_names()
            for name in names:
                if name.startswith(MPRIS_PREFIX):
                    await self._attach_player(name)

        # ── Player management ─────────────────────────────────────────────────

        async def _attach_player(self, name: str) -> None:
            if name in self._players or not self._bus:
                return

            try:
                intro = await self._bus.introspect(name, "/org/mpris/MediaPlayer2")
                obj = self._bus.get_proxy_object(name, "/org/mpris/MediaPlayer2", intro)

                player = obj.get_interface("org.mpris.MediaPlayer2.Player")
                props = obj.get_interface("org.freedesktop.DBus.Properties")

                if not isinstance(player, PlayerInterface):
                    raise RuntimeError(f"{name}: Player interface not available.")
                if not isinstance(props, PropertiesInterface):
                    raise RuntimeError(f"{name}: Properties interface not available.")

                props.on_properties_changed(
                    lambda iface, changed, _invalid: self._on_properties_changed(
                        name, iface, changed
                    )
                )

                self._players[name] = player
                self._props[name] = props
                self._status[name] = await player.get_playback_status()

                self._reevaluate_active_player()
                await self._emit_track_info_for(name, metadata=None)

            except Exception:
                _log.exception("Failed to attach player %r", name)

        def _detach_player(self, name: str) -> None:
            self._players.pop(name, None)
            self._props.pop(name, None)
            self._status.pop(name, None)

            if self._active_player == name:
                self._active_player = None
                self._reevaluate_active_player()

        # ── Active-player selection ───────────────────────────────────────────

        def _reevaluate_active_player(self) -> None:
            playing = [n for n, s in self._status.items() if s == "Playing"]
            if not playing:
                return

            selected = self._pick_by_priority(playing)
            if selected != self._active_player:
                self._active_player = selected
                asyncio.run_coroutine_threadsafe(self._emit_full_state(selected), _loop)

        @staticmethod
        def _pick_by_priority(names: list[str]) -> str:
            for preferred in PLAYER_PRIORITY:
                if preferred in names:
                    return preferred
            return names[0]

        # ── Signal handlers ───────────────────────────────────────────────────

        def _on_name_owner_changed(self, name: str, _old: str, new: str) -> None:
            if not name.startswith(MPRIS_PREFIX):
                return
            if new:
                asyncio.run_coroutine_threadsafe(self._attach_player(name), _loop)
            else:
                self._detach_player(name)

        def _on_properties_changed(
            self,
            name: str,
            iface: str,
            changed: "dict[str, Variant]",
        ) -> None:
            if iface != "org.mpris.MediaPlayer2.Player":
                return

            if "PlaybackStatus" in changed:
                raw_status = changed["PlaybackStatus"].value
                self._status[name] = raw_status if isinstance(raw_status, str) else ""
                self._reevaluate_active_player()
                if name == self._active_player:
                    self._emit_playback_status(name)

            if "Metadata" in changed and name == self._active_player:
                asyncio.run_coroutine_threadsafe(
                    self._emit_track_info_for(name, metadata=changed["Metadata"]),
                    _loop,
                )

        # ── Emitters ──────────────────────────────────────────────────────────

        async def _emit_full_state(self, name: str) -> None:
            await self._emit_track_info_for(name, metadata=None)
            self._emit_playback_status(name)

        async def _emit_track_info_for(
            self,
            name: str,
            metadata: "Variant | None",
        ) -> None:
            try:
                if metadata is not None:
                    raw: "dict[str, Variant]" = (
                        metadata.value if isinstance(metadata.value, dict) else {}
                    )
                else:
                    player = self._players.get(name)
                    if player is None:
                        return
                    raw = await player.get_metadata()

                if not raw:
                    return

                info = TrackInfo(
                    title=_extract_title(raw),
                    artist=_extract_artist(raw),
                )
                self._notify_track_changed(name, info)

            except Exception:
                _log.exception("Error emitting track info for %r", name)

        def _emit_playback_status(self, name: str) -> None:
            raw = self._status.get(name, "")
            self._notify_playback_status_changed(name, _playback_status_from_mpris(raw))

# ─── Fallback (unsupported platform) ─────────────────────────────────────────

else:

    class TracksInfoTracker(BaseTracksInfoTracker):
        """No-op tracker for unsupported platforms."""

        def start(self) -> None:
            pass
