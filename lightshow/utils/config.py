import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Type, TypedDict, TypeVar

from lightshow.audio.audio_types import AudioDevice
from lightshow.devices import DEVICES_STR_TYPES
from lightshow.devices.device import Device
from lightshow.utils.logger import Logger


class DeviceConfigType(TypedDict):
    type: Type[DEVICES_STR_TYPES]
    props: Dict[str, Any]


T = TypeVar("T")


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore

    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Config:
    def __init__(self, config_file="config.json"):
        if os.name == "nt":  # Windows
            base_dir = Path(
                os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
        else:  # Linux / macOS
            base_dir = Path(
                os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )

        base_dir = base_dir.expanduser().resolve()

        self.config_folder = base_dir / ".LightShow"
        self.logger = Logger("ConfigManager")
        if not self.config_folder.exists():
            self.logger.info("Config folder doesn't exists... Creating it...")
            self.config_folder.mkdir()
        self.config_file = self.config_folder / config_file
        self.settings = self.load_config_file()
        self.reload_config()

    def load_config_file(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.info(
                f"Config file {self.config_file} not found. Using default settings."
            )
            return {}
        except json.JSONDecodeError:
            self.logger.error(
                f"Config file {self.config_file} is not a valid JSON. Using default settings."
            )
            return {}

    def reload_config(self):
        self.chunk_size = self.get("chunk_size", 1024)
        self.audio_device = AudioDevice.from_dict(
            self.get(
                "audio_device", AudioDevice(is_default=True, is_loopback=True).to_dict()
            )
        )  # Default to loopback speaker.
        self.max_fps = self.get("max_fps", 30)
        self.audio_sensitivity = self.get(
            "audio_sensitivity", 2.0
        )  # Linux default is higher
        self.devices: Dict[str, DeviceConfigType] = self.get("devices", {})

    def get(self, key, default: T) -> T:
        return self.settings.get(key, default)

    def save(self):
        with open(self.config_file, "w") as f:
            self.settings["chunk_size"] = self.chunk_size
            self.settings["audio_device"] = self.audio_device.to_dict()
            self.settings["max_fps"] = self.max_fps
            self.settings["audio_sensitivity"] = self.audio_sensitivity
            self.settings["devices"] = self.devices
            json.dump(self.settings, f, indent=4)
        self.logger.info(f"Configuration saved to {self.config_file}")


global_config = Config()
live_devices: Dict[str, Device] = {}
