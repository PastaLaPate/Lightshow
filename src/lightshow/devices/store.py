from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from PySide6.QtCore import QObject, QTimer, Signal

from lightshow.core.logger import Logger
from lightshow.devices.device import Device
from lightshow.devices.registry import DEVICE_CLASSES
from lightshow.devices.status import DeviceStatus
from lightshow.devices.types import BaseDeviceSettings, DeviceConfigType, DeviceTypeName
from lightshow.document.history import global_history
from lightshow.gui.utils.async_tasks import JobData, TaskContext, TaskRunner

logger = Logger("DeviceStore")


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
        logger.debug(f"Creating {self.config.name} ({self.type_name})'s instance.")
        device_type = DEVICE_CLASSES[self.type_name]
        self._device = device_type(self.config)
        self.status = DeviceStatus.DISCONNECTED
        return self._device


class DeviceStore(QObject):
    device_added = Signal(str)  # device_id
    device_removed = Signal(str)  # device_id
    device_renamed = Signal(str, str)  # device_id, new_name
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

    def _raw_create_device(self, type_name: DeviceTypeName, device_id: str) -> None:
        cls = DEVICE_CLASSES[type_name]
        cfg: BaseDeviceSettings = cls.CONFIG_SCHEMA(id=device_id)
        self._entries[device_id] = DeviceEntry(type_name, cfg)
        self.device_added.emit(device_id)
        self._save_timer.start()

    def _restore_device(self, device_id: str, entry: DeviceEntry) -> None:
        self._entries[device_id] = entry
        self.device_added.emit(device_id)
        self._save_timer.start()

    def _raw_delete_device(self, device_id: str) -> None:
        self.disconnect_device(device_id)
        del self._entries[device_id]
        self.device_removed.emit(device_id)
        self._save_timer.start()

    def _raw_update(self, device_id: str, field: str, value: Any) -> None:
        e = self._entries[device_id]
        setattr(e.config, field, value)
        if e._device is not None:
            e._device.on_config_changed(field)
        self.device_changed.emit(device_id, field)
        self._save_timer.start()

    def _raw_rename(self, device_id: str, value: str) -> None:
        self._raw_update(device_id, "name", value)
        self.device_renamed.emit(device_id, value)

    def new_device(
        self, type_name: DeviceTypeName, device_id: str | None = None
    ) -> str:
        device_id = device_id or uuid4().hex
        self._raw_create_device(type_name, device_id)
        global_history.record(
            undo=lambda: self._raw_delete_device(device_id),
            redo=lambda: self._raw_create_device(type_name, device_id),
        )
        return device_id

    def delete_device(self, device_id: str) -> None:
        entry = self._entries[device_id]
        self._raw_delete_device(device_id)
        global_history.record(
            undo=lambda: self._restore_device(device_id, entry),
            redo=lambda: self._raw_delete_device(device_id),
        )

    def rename_device(self, device_id: str, new_name: str) -> None:
        old_name = self._entries[device_id].config.name
        self._raw_rename(device_id, new_name)
        global_history.record(
            undo=lambda: self._raw_rename(device_id, old_name),
            redo=lambda: self._raw_rename(device_id, new_name),
        )

    def update(self, device_id: str, field: str, value: Any) -> bool:
        old = getattr(self._entries[device_id].config, field)
        if old == value:
            return True
        try:
            self._raw_update(device_id, field, value)
        except ValidationError as error:
            logger.warning("Rejected %s=%r: %s", field, value, error)
            self.device_changed.emit(device_id, field)
            return False
        global_history.record(
            undo=lambda: self._raw_update(device_id, field, old),
            redo=lambda: self._raw_update(device_id, field, value),
        )
        return True

    def _set_status(self, device_id: str, status: DeviceStatus) -> None:
        self._entries[device_id].status = status
        self.device_status_changed.emit(device_id, status)

    def connect_device(
        self, device_id: str, on_result: Callable[[bool, str], None] | None = None
    ) -> None:
        """Connects a device.

        Args:
            device_id (str): the device's id to connect, must be in entries.
            on_result (str): Ok, error_msg.
        """
        entry: DeviceEntry = self._entries[device_id]

        def work(ctx: TaskContext):
            ctx.progress("Connecting...")
            entry.device.connect(fatal_non_discovery=True)
            return entry.device.ready

        def done(ready: bool):
            self._set_status(
                device_id,
                DeviceStatus.CONNECTED if ready else DeviceStatus.DISCONNECTED,
            )
            if on_result:
                on_result(ready, "" if ready else "Device did not become ready")

        def error(exc: Exception):
            self._set_status(device_id, DeviceStatus.DISCONNECTED)
            if on_result:
                on_result(False, f"Connection failed for {device_id}: {exc}")

        if TaskRunner.get().submit(
            JobData(work, device_id, on_done=done, on_error=error),
        ):
            self._set_status(device_id, DeviceStatus.CONNECTING)

    def disconnect_device(self, device_id: str) -> None:
        e = self._entries[device_id]
        if e._device is not None:
            e.device.disconnect()
            e._device = None
        self._set_status(device_id, DeviceStatus.DISCONNECTED)

    def shutdown(self) -> None:
        for device_id in list(self._entries):
            self.disconnect_device(device_id)
        self._save_cb()
