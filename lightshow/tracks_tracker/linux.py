import os

if not os.name == "posix":
    raise ImportError("This module is only for Linux.")

import asyncio
import threading
from typing import Callable, Final, Protocol, runtime_checkable

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from dbus_next.signature import Variant

from lightshow.tracks_tracker.abstract_tracker import ATrackTracker
from lightshow.tracks_tracker.types import PlaybackStatus, TrackInfo
from lightshow.utils import Logger


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


_loop: Final[asyncio.AbstractEventLoop] = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


MPRIS_PREFIX: Final = "org.mpris.MediaPlayer2."

PLAYER_PRIORITY: Final[list[str]] = [
    "org.mpris.MediaPlayer2.deezer",
    "org.mpris.MediaPlayer2.spotify",
    "org.mpris.MediaPlayer2.vlc",
    "org.mpris.MediaPlayer2.mpv",
    "org.mpris.MediaPlayer2.firefox",
    "org.mpris.MediaPlayer2.chromium",
]

_log = Logger("TracksInfoTracker")


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


def _playback_status_from_mpris(raw: str) -> PlaybackStatus:
    mapping: dict[str, PlaybackStatus] = {
        "Playing": PlaybackStatus.PLAYING,
        "Paused": PlaybackStatus.PAUSED,
        "Stopped": PlaybackStatus.STOPPED,
    }
    return mapping.get(raw, PlaybackStatus.STOPPED)


class LinuxTracksInfoTracker(ATrackTracker):
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
