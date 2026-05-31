"""
lightshow/utils/config.py

Design:
  - Setting[T]        generic dataclass carrying id, name, type, default, …
  - _Settings         namespace object: SETTINGS.SHOW_SPECTRUM : Setting[bool]
  - SettingsMap       typed dict-like: config.settings[SETTINGS.SHOW_SPECTRUM] → bool
  - SETTINGS_CATEGORIES  list[SettingListItem] for the UI tree (icons, tabs, order)
  - Config            owns .settings: SettingsMap + unmanaged attrs
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar, Dict, Generic, Iterator, TypeVar

import distro

from lightshow.audio.audio_types import AudioDevice
from lightshow.devices.device import Device
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.utils.logger import Logger

# ──────────────────────────────────────────────────────────────────────────────
# Generic Setting[T]
# ──────────────────────────────────────────────────────────────────────────────

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


@dataclass
class Setting(Generic[T]):
    """
    A single configurable value, typed by T.

    Usage
    -----
    SHOW_SPECTRUM = Setting[bool](
        id="ui.layout.show_spectrum",
        name="Show Spectrum",
        description="Show the spectrum visualization",
        type=bool,
        default=True,
    )

    config.settings[SETTINGS.SHOW_SPECTRUM]         # → bool  ✓
    config.settings[SETTINGS.MAX_FPS]               # → int   ✓
    """

    id: str
    name: str
    description: str
    type: type[T]
    default: T
    options: list[T] | None = None


# ──────────────────────────────────────────────────────────────────────────────
# SettingsMap — typed dict-like container
# ──────────────────────────────────────────────────────────────────────────────


class SettingsMap:
    """
    Typed key/value store indexed by Setting[T] instances.

    config.settings[SETTINGS.SHOW_SPECTRUM]          # bool
    config.settings[SETTINGS.SENSITIVITY]            # float
    config.settings[SETTINGS.BEAT_ALGORITHM]         # str

    The generic __getitem__ / __setitem__ propagate T so type-checkers
    (Pylance, mypy) infer the return type from the Setting's type parameter.
    """

    def __init__(self, all_settings: list[Setting[Any]]) -> None:
        self._store: dict[str, Any] = {}
        self._meta: dict[str, Setting[Any]] = {s.id: s for s in all_settings}

    # ── generic typed accessors ───────────────────────────────────────────────

    def __getitem__(self, key: Setting[T]) -> T:
        return self._store[key.id]  # type: ignore[return-value]

    def __setitem__(self, key: Setting[T], value: T) -> None:
        self._store[key.id] = value

    def __contains__(self, key: Setting[Any]) -> bool:
        return key.id in self._store

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    # ── raw id-based access (for serialisation / dialog) ─────────────────────

    def get_by_id(self, setting_id: str) -> Any:
        return self._store[setting_id]

    def set_by_id(self, setting_id: str, value: Any) -> None:
        if setting_id not in self._meta:
            raise KeyError(f"Unknown setting id: {setting_id!r}")
        meta = self._meta[setting_id]
        self._store[setting_id] = _coerce(value, meta)

    def as_dict(self) -> dict[str, Any]:
        """Flat {id: value} snapshot — used for serialisation and the dialog."""
        return dict(self._store)

    def ids(self) -> list[str]:
        return list(self._meta)

    # ── internal ─────────────────────────────────────────────────────────────

    def _load_defaults(self) -> None:
        for sid, meta in self._meta.items():
            self._store[sid] = meta.default

    def _load_raw(self, raw: dict[str, Any]) -> None:
        for sid, meta in self._meta.items():
            raw_value = raw.get(sid, meta.default)
            self._store[sid] = _coerce(raw_value, meta)


def _coerce(value: Any, meta: Setting[Any]) -> Any:
    """Cast *value* to meta.type, falling back to meta.default on failure."""
    try:
        if meta.type is bool:
            return bool(value)
        if meta.type is int and isinstance(value, (int, float, str)):
            return int(value)
        if meta.type is float and isinstance(value, (int, float, str)):
            return float(value)
        if meta.type is str:
            return str(value) if value is not None else ""
        return value  # list / passthrough
    except ValueError, TypeError:
        return meta.default


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS namespace
# ──────────────────────────────────────────────────────────────────────────────


class _Settings:
    """
    Enum-like namespace of all managed settings.

    Access pattern:   SETTINGS.SHOW_SPECTRUM          → Setting[bool]
                      SETTINGS.SHOW_SPECTRUM.id        → "ui.layout.show_spectrum"
                      config.settings[SETTINGS.SHOW_SPECTRUM]  → bool
    """

    # ── UI › Layout ───────────────────────────────────────────────────────────

    SHOW_SPECTRUM: Setting[bool] = Setting(
        id="ui.layout.show_spectrum",
        name="Show Spectrum",
        description="Show the spectrum visualization",
        type=bool,
        default=True,
    )

    SHOW_BEAT_DETECTION: Setting[bool] = Setting(
        id="ui.layout.show_beat_detection",
        name="Show Beat Detection",
        description="Show the beat detection visualization",
        type=bool,
        default=True,
    )

    # ── Audio › General ───────────────────────────────────────────────────────

    SENSITIVITY: Setting[float] = Setting(
        id="audio.general.sensitivity",
        name="Sensitivity",
        description="Audio input sensitivity multiplier",
        type=float,
        default=2.0,
    )

    CHUNK_SIZE: Setting[int] = Setting(
        id="audio.general.chunk_size",
        name="Chunk Size",
        description="Number of audio frames per processing buffer",
        type=int,
        default=1024,
        options=[256, 512, 1024, 2048, 4096],
    )

    # ── Audio › Beat detection ────────────────────────────────────────────────

    BEAT_ALGORITHM: Setting[str] = Setting(
        id="audio.detection.beat_algorithm",
        name="Algorithm",
        description="Beat detection algorithm",
        type=str,
        default="Percentile",
        options=["Average Diff", "Percentile"],
    )

    # ── Performance › General ─────────────────────────────────────────────────

    MAX_FPS: Setting[int] = Setting(
        id="performance.general.max_fps",
        name="Max FPS",
        description="Maximum frames per second for light output",
        type=int,
        default=30,
        options=[10, 20, 30, 60],
    )

    # ── helpers ───────────────────────────────────────────────────────────────

    def all(self) -> list[Setting[Any]]:
        """Return every Setting defined on this namespace."""
        return [v for v in vars(type(self)).values() if isinstance(v, Setting)]

    def by_id(self, setting_id: str) -> Setting[Any]:
        for s in self.all():
            if s.id == setting_id:
                return s
        raise KeyError(setting_id)


SETTINGS = _Settings()


# ──────────────────────────────────────────────────────────────────────────────
# UI tree helpers (categories / tabs)
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class SettingTab:
    id: str
    name: str
    description: str
    settings: list[Setting[Any]] = field(default_factory=list)


@dataclass
class SettingListItem:
    id: str
    name: str
    description: str
    icon: str | None = None
    tabs: list[SettingTab] = field(default_factory=list)


# Declares the UI tree order, icons, and tab grouping.
# The Setting objects are the single source of truth — referenced, not copied.
SETTINGS_CATEGORIES: list[SettingListItem] = [
    SettingListItem(
        id="ui",
        name="User Interface",
        description="Settings related to the user interface",
        icon="icons/ui.svg",
        tabs=[
            SettingTab(
                id="ui.general",
                name="General",
                description="General UI settings",
                settings=[],  # empty tab kept for future use
            ),
            SettingTab(
                id="ui.layout",
                name="Layout",
                description="Change the UI layout",
                settings=[
                    SETTINGS.SHOW_SPECTRUM,
                    SETTINGS.SHOW_BEAT_DETECTION,
                ],
            ),
        ],
    ),
    SettingListItem(
        id="audio",
        name="Audio",
        description="Audio capture and processing settings",
        icon="icons/audio.svg",
        tabs=[
            SettingTab(
                id="audio.general",
                name="General",
                description="General audio settings",
                settings=[
                    SETTINGS.SENSITIVITY,
                    SETTINGS.CHUNK_SIZE,
                ],
            ),
            SettingTab(
                id="audio.detection",
                name="Beat Detection",
                description="Beat detection settings",
                settings=[
                    SETTINGS.BEAT_ALGORITHM,
                ],
            ),
        ],
    ),
    SettingListItem(
        id="performance",
        name="Performance",
        description="Performance and rendering settings",
        icon="icons/performance.svg",
        tabs=[
            SettingTab(
                id="performance.general",
                name="General",
                description="General performance settings",
                settings=[
                    SETTINGS.MAX_FPS,
                ],
            ),
        ],
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Metadata / env constants
# ──────────────────────────────────────────────────────────────────────────────


class DeviceConfigType(dict):  # keep TypedDict-style usage working
    type: "DeviceTypeName"
    props: Dict[str, Any]


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


VERSION = version("lightshow")
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))
if platform.system() == "Windows":
    OS = f"Windows {platform.release()}"
elif platform.system() == "Darwin":
    OS = f"macOS {platform.mac_ver()[0]}"
else:
    OS = distro.name(pretty=True)
ARCH = " ".join(platform.architecture())


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────


class Config:
    """
    Application configuration.

    Managed settings (declared in SETTINGS):
        config.settings[SETTINGS.SHOW_SPECTRUM]   → bool
        config.settings[SETTINGS.MAX_FPS]         → int

    Unmanaged settings (own attrs, custom UI):
        config.audio_device   → AudioDevice
        config.devices        → dict[str, DeviceConfigType]
    """

    _UNMANAGED: ClassVar[set[str]] = {"audio_device", "devices"}

    def __init__(self, config_file: str = "config.json") -> None:
        if os.name == "nt":
            base_dir = Path(
                os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            )
        else:
            base_dir = Path(
                os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
            )

        base_dir = base_dir.expanduser().resolve()
        self.config_folder = base_dir / ".LightShow"
        self.logger = Logger("ConfigManager")

        if not self.config_folder.exists():
            self.logger.info("Config folder doesn't exist — creating it…")
            self.config_folder.mkdir(parents=True)

        self.config_file = self.config_folder / config_file
        self._raw: dict[str, Any] = self._load_file()

        # Unmanaged fields
        self.audio_device: AudioDevice = AudioDevice.from_dict(
            self._raw.get(
                "audio_device",
                AudioDevice(is_default=True, is_loopback=True).to_dict(),
            )
        )
        self.devices: Dict[str, DeviceConfigType] = self._raw.get("devices", {})

        # Managed settings
        self.settings: SettingsMap = SettingsMap(SETTINGS.all())
        self.settings._load_raw(self._raw)

    # ── private ───────────────────────────────────────────────────────────────

    def _load_file(self) -> dict[str, Any]:
        try:
            with open(self.config_file) as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.info(f"{self.config_file} not found — using defaults.")
            return {}
        except json.JSONDecodeError:
            self.logger.error(f"{self.config_file} is invalid JSON — using defaults.")
            return {}

    # ── public ────────────────────────────────────────────────────────────────

    def apply(self, changes: dict[str, Any]) -> None:
        """
        Apply a batch of {setting_id: new_value} from the settings UI.
        Unknown keys are logged and skipped.
        """
        for key, value in changes.items():
            try:
                self.settings.set_by_id(key, value)
                self._raw[key] = self.settings.get_by_id(key)
            except KeyError:
                self.logger.warn(f"apply(): unknown setting id {key!r} — ignored")

    def save(self) -> None:
        # Persist managed settings
        self._raw.update(self.settings.as_dict())

        # Persist unmanaged settings
        self._raw["audio_device"] = self.audio_device.to_dict()
        self._raw["devices"] = self.devices

        with open(self.config_file, "w") as f:
            json.dump(self._raw, f, indent=4)

        self.logger.info(f"Configuration saved to {self.config_file}")

    def get_raw(self, key: str, default: T) -> T:
        """Low-level raw access — prefer config.settings[SETTINGS.X]."""
        return self._raw.get(key, default)


global_config = Config()
live_devices: Dict[str, Device] = {}
