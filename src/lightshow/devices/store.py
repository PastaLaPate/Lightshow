from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from PySide6.QtCore import QObject, QTimer, Signal

from lightshow.core.config import DeviceConfigType
from lightshow.core.logger import Logger
from lightshow.devices import DEVICE_CLASSES
from lightshow.devices.device import BaseDeviceSettings, Device
from lightshow.devices.devices_types import DeviceTypeName

logger = Logger("DeviceStore")


class DeviceStatus(IntEnum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()


@dataclass
class DeviceEntry:
    type_name: DeviceTypeName
    config: BaseDeviceSettings
    _device: Device | None = None
    status: DeviceStatus = DeviceStatus.DISCONNECTED

    @property
    def device(self) -> Device:
        if self._device:
            return self._device
        logger.debug(f"Created {self.config.name} ({self.type_name.value})'s instance.")
        device_type = DEVICE_CLASSES[self.type_name]
        self._device = device_type(self.config)
        self.status = DeviceStatus.DISCONNECTED
        return self._device


class DeviceStore(QObject):
    device_added = Signal(str)  # device_id
    device_removed = Signal(str)  # device_id
    device_changed = Signal(str, str)  # device_id, field
    device_status_changed = Signal(str, object)  # device_id, New status

    def __init__(self, save_cb: Callable[[], None]):
        super().__init__()
        self._save_cb = save_cb
        self._entries: dict[str, DeviceEntry] = {}
        self._quarantine: dict[str, Any] = {}

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._save_cb)

    def get(self, device_id: str) -> DeviceEntry:
        return self._entries[device_id]

    def get_instance(self, device_id: str) -> Device:
        return self._entries[device_id].device

    def all(self) -> dict[str, DeviceEntry]:
        return self._entries

    def load(self, raw: dict[str, DeviceConfigType]) -> None:
        for device_id, item in raw.items():
            cls = DEVICE_CLASSES.get(item.get("type"))
            if cls is None:
                logger.warning(
                    "Unknown device type %r for %s, placing in quarantine",
                    item.get("type"),
                    device_id,
                )
                self._quarantine[device_id] = item
                continue
            try:
                schema: BaseDeviceSettings = cls.CONFIG_SCHEMA
                cfg = schema.model_validate({**item.get("props", {}), "id": device_id})
            except ValidationError as e:
                logger.error(
                    "Invalid config for %s: %s, placing in quarantine", device_id, e
                )
                self._quarantine[device_id] = item
                continue
            self._entries[device_id] = DeviceEntry(item["type"], cfg)
            self.device_added.emit(device_id)

    def dump(self) -> dict[str, dict]:
        out = {
            i: {"type": e.type_name, "props": e.config.model_dump(mode="json")}
            for i, e in self._entries.items()
        }
        return out | self._quarantine

    def new_device(self, type_name: DeviceTypeName) -> str:
        cls = DEVICE_CLASSES[type_name]
        device_id = uuid4().hex
        cfg: BaseDeviceSettings = cls.CONFIG_SCHEMA(id=device_id)
        self._entries[device_id] = DeviceEntry(type_name, cfg)
        self.device_added.emit(device_id)
        self._save_timer.start()
        return device_id

    def delete_device(self, device_id: str) -> None:
        self.disconnect_device(device_id)
        del self._entries[device_id]
        self.device_removed.emit(device_id)
        self._save_timer.start()

    def update(self, device_id: str, field: str, value: Any) -> bool:
        e = self._entries[device_id]
        if getattr(e.config, field) == value:
            return True
        try:
            setattr(e.config, field, value)
        except ValidationError as error:
            logger.warning("Rejected %s=%r: %s", field, value, error)
            self.device_changed.emit(device_id, field)
            return False
        if e._device is not None:
            e._device.on_config_changed(field)
        self.device_changed.emit(device_id, field)
        self._save_timer.start()
        return True

    def _set_status(self, device_id: str, status: DeviceStatus) -> None:
        self._entries[device_id].status = status
        self.device_status_changed.emit(device_id, status)

    def connect_device(self, device_id: str) -> tuple[bool, str]:
        """Connects a device.

        Args:
            device_id (str): the device's id to connect, must be in entries.

        Returns:
            tuple[bool, str]: True and "" if connected with no error, else False and error string. Does not ensure the device's ready.
        """
        e: DeviceEntry = self._entries[device_id]
        self._set_status(device_id, DeviceStatus.CONNECTING)
        try:
            e.device.connect(fatal_non_discovery=True)
        except ConnectionError as error:
            logger.error("Connection failed for %s: %s", device_id, error)
            return False, f"Connection failed for {device_id}: {error}"
        ok = e.device.ready
        self._set_status(
            device_id, DeviceStatus.CONNECTED if ok else DeviceStatus.DISCONNECTED
        )
        return True, ""

    def disconnect_device(self, device_id: str):
        e = self._entries[device_id]
        if e._device is not None:
            e.device.disconnect()
            e._device = None
        self._set_status(device_id, DeviceStatus.DISCONNECTED)

    def shutdown(self) -> None:
        for device_id in list(self._entries):
            self.disconnect_device(device_id)
        self._save_cb()
