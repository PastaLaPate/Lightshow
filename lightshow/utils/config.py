import json
import os
import platform
import sys
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar, Dict, TypedDict, TypeVar

import distro

from lightshow.audio.audio_types import AudioDevice
from lightshow.devices.device import Device
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.utils.logger import Logger


class DeviceConfigType(TypedDict):
    type: DeviceTypeName
    props: Dict[str, Any]


@dataclass
class Setting:
    id: str  # e.g. audio.general.sensitivity
    name: str
    description: str
    type: type[int | float | str | bool | list]
    options: list | None = None
    default: int | float | str | bool | list | None = None


@dataclass
class SettingListItem:
    id: str
    name: str
    description: str
    icon: str | None = None
    tabs: list["SettingTab"] = field(default_factory=list)


@dataclass
class SettingTab:
    id: str
    name: str
    description: str
    settings: list[Setting] = field(default_factory=list)


SETTINGS: list[SettingListItem] = [
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
                settings=[],
            ),
            SettingTab(
                id="ui.layout",
                name="Layout",
                description="Change the ui's layout",
                settings=[
                    Setting(
                        id="ui.layout.show_spectrum",
                        name="Show Spectrum",
                        description="Show the spectrum visualization",
                        type=bool,
                        default=True,
                    ),
                    Setting(
                        id="ui.layout.show_beat_detection",
                        name="Show Beat Detection",
                        description="Show the beat detection visualization",
                        type=bool,
                        default=True,
                    ),
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
                    Setting(
                        id="audio.general.sensitivity",
                        name="Sensitivity",
                        description="Audio input sensitivity multiplier",
                        type=float,
                        default=2.0,
                    ),
                    Setting(
                        id="audio.general.chunk_size",
                        name="Chunk size",
                        description="Number of audio frames per processing buffer",
                        type=int,
                        options=[256, 512, 1024, 2048, 4096],
                        default=1024,
                    ),
                ],
            ),
            SettingTab(
                id="audio.detection",
                name="Beat detection",
                description="Beat detection settings",
                settings=[
                    Setting(
                        id="audio.detection.beat_algorithm",
                        name="Algorithm",
                        description="Beat detection algorithm",
                        type=list,
                        options=["Average Diff", "Percentile"],
                        default="Percentile",
                    ),
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
                    Setting(
                        id="performance.general.max_fps",
                        name="Max FPS",
                        description="Maximum frames per second for light output",
                        type=int,
                        options=[10, 20, 30, 60],
                        default=30,
                    ),
                ],
            ),
        ],
    ),
]

# Flat index: setting.id → Setting, built once at import time
_SETTINGS_INDEX: dict[str, Setting] = {
    setting.id: setting
    for item in SETTINGS
    for tab in item.tabs
    for setting in tab.settings
}


# ─────────────────────────────────────────────
# Typed attribute bag auto-generated from tree
# ─────────────────────────────────────────────


class _ConfigAttrs:
    """
    Holds one typed attribute per Setting in SETTINGS.
    Config inherits this so `global_config.max_fps` works with
    full type-checker support.

    When you add a Setting to SETTINGS, add the matching
    attribute annotation here — that's the only manual step.
    """

    audio_sensitivity: float
    chunk_size: int
    max_fps: int
    show_spectrum: bool
    show_beat_detection: bool
    beat_algorithm: str


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

T = TypeVar("T")


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


VERSION = version("lightshow")
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))
if platform.system() == "Windows":
    OS = f"Windows {platform.release()}"
elif platform.system() == "Darwin":
    OS = f"macOS {platform.mac_ver()[0]}"
elif platform.system() == "Linux":
    OS = distro.name(pretty=True)
ARCH = " ".join(platform.architecture())


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────


class Config(_ConfigAttrs):
    # Settings that live outside the SETTINGS tree (device map, audio device)
    # are declared here explicitly — they have their own UIs.
    _UNMANAGED: ClassVar[set[str]] = {"audio_device", "devices"}

    def __init__(self, config_file: str = "config.json"):
        if os.name == "nt":
            base_dir = Path(
                os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
        else:
            base_dir = Path(
                os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")
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
        self.audio_device = AudioDevice.from_dict(
            self._raw.get(
                "audio_device",
                AudioDevice(is_default=True, is_loopback=True).to_dict(),
            )
        )
        self.devices: Dict[str, DeviceConfigType] = self._raw.get("devices", {})

        # Auto-load every managed setting from the tree
        self._reload_managed()

    # ── private ──────────────────────────────

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

    def _reload_managed(self) -> None:
        """Set one attribute per entry in SETTINGS, falling back to default."""
        for setting_id, setting in _SETTINGS_INDEX.items():
            raw_value = self._raw.get(setting_id, setting.default)
            # Coerce to the declared type so attributes are always typed correctly
            try:
                if setting.type is bool:
                    value = bool(raw_value)
                elif setting.type is int and isinstance(raw_value, (int, float, str)):
                    value = int(raw_value)
                elif setting.type is float and isinstance(raw_value, (int, float, str)):
                    value = float(raw_value)
                elif setting.type is str:
                    value = str(raw_value) if raw_value is not None else ""
                else:
                    value = raw_value  # list / passthrough
            except ValueError, TypeError:
                value = setting.default
            setattr(self, setting_id, value)

    # ── public ───────────────────────────────

    def apply(self, changes: dict[str, int | float | str | bool | list]) -> None:
        """
        Apply a batch of {setting_id: new_value} coming from the settings UI.
        Unknown keys are silently ignored.
        """
        for key, value in changes.items():
            if key in _SETTINGS_INDEX:
                self._raw[key] = value
                setattr(self, key, value)
            else:
                self.logger.warn(f"apply(): unknown setting id '{key}' — ignored")

    def save(self) -> None:
        # Persist all managed settings
        for setting_id in _SETTINGS_INDEX:
            self._raw[setting_id] = getattr(self, setting_id)

        # Persist unmanaged settings
        self._raw["audio_device"] = self.audio_device.to_dict()
        self._raw["devices"] = self.devices

        with open(self.config_file, "w") as f:
            json.dump(self._raw, f, indent=4)

        self.logger.info(f"Configuration saved to {self.config_file}")

    def get(self, key: str, default: T) -> T:
        return self._raw.get(key, default)  # type: ignore[return-value]


global_config = Config()
live_devices: Dict[str, Device] = {}
