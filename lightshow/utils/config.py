import json
import os
import sys
from typing import Any, Dict, Type, TypeVar, TypedDict

from lightshow.devices import DEVICES_STR_TYPES
from lightshow.devices.device import Device


class DeviceConfigType(TypedDict):
    type: Type[DEVICES_STR_TYPES]
    props: Dict[str, Any]


T = TypeVar("T")


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.settings = self.load_config_file()
        self.reload_config()

    def load_config_file(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {self.config_file} not found. Using default settings.")
            return {}

    def reload_config(self):
        self.chunk_size = self.get("chunk_size", 1024)
        self.device_index = self.get("device_index", -2)  # Auto-detect if -1
        self.max_fps = self.get("max_fps", 30)
        self.devices: Dict[str, DeviceConfigType] = self.get("devices", {})

    def get(self, key, default: T = None) -> T:
        return self.settings.get(key, default)

    def save(self):
        with open(self.config_file, "w") as f:
            self.settings["chunk_size"] = self.chunk_size
            self.settings["device_index"] = self.device_index
            self.settings["max_fps"] = self.max_fps
            self.settings["devices"] = self.devices
            json.dump(self.settings, f, indent=4)
        print(f"Configuration saved to {self.config_file}")


global_config = Config()
live_devices: Dict[str, Device] = {}
