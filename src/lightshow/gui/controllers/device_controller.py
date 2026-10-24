from typing import Any

from PySide6.QtCore import QObject

from lightshow.core.config import global_config
from lightshow.core.events import notifications
from lightshow.devices.events import device_events
from lightshow.devices.types import DeviceTypeName
from lightshow.document.history import global_history
from lightshow.gui.utils import ui_signals


class DeviceController(QObject):
    def __init__(self) -> None:
        super().__init__(None)

        ui_signals.devices_req.create.connect(self.handle_create_device)
        ui_signals.devices_req.duplicate.connect(self.handle_duplicate_device)
        ui_signals.devices_req.rename.connect(self.handle_rename_device)
        ui_signals.devices_req.set_field.connect(self.handle_set_field)
        ui_signals.devices_req.delete.connect(self.handle_delete_device)

        ui_signals.devices_req.connect_.connect(self.handle_connect_device)
        ui_signals.devices_req.disconnect_.connect(self.handle_disconnect_device)

        # global_config.device_store.device_added.connect(ui_signals.new_device) Handled via handle_create_device, to attribute a name
        global_config.device_store.device_renamed.connect(device_events.renamed)
        global_config.device_store.device_changed.connect(self.send_field_set)
        global_config.device_store.device_removed.connect(device_events.deleted)
        global_config.device_store.device_status_changed.connect(
            device_events.status_changed
        )

    def handle_create_device(self, device_type: DeviceTypeName, name: str | None):
        with global_history.transaction(
            f"Create and rename device of type {device_type}"
        ):
            new_device_id = global_config.device_store.new_device(device_type)
            global_config.device_store.rename_device(
                new_device_id,
                name or f"Device {len(global_config.device_store.all()) + 1}",
            )
            device_events.created.emit(new_device_id)

    def handle_duplicate_device(self, device_id: str):
        store = global_config.device_store
        with global_history.transaction(f"Duplicate {device_id}"):
            src = store.get(device_id)
            data = src.config.model_dump()
            data.pop("id")  # Avoid duplicating ids
            data["name"] = f"{src.config.name} (copy)"
            new_device_id = store.new_device(src.type_name, config_data=data)
            device_events.created.emit(new_device_id)

    def handle_rename_device(self, id: str, new_name: str):
        if not self.id_exists(id) or new_name == "":
            return

        with global_history.transaction(f"Rename device {id} to {new_name}"):
            global_config.device_store.rename_device(id, new_name)

    def handle_set_field(self, id: str, field: str, value: Any):
        if not self.id_exists(id) or field == "":
            return

        with global_history.transaction(f"Set {id}'s {field} to {value}"):
            global_config.device_store.update(id, field, value)

    def handle_delete_device(self, id: str):
        if not self.id_exists(id):
            return

        with global_history.transaction(f"Delete device {id}"):
            global_config.device_store.delete_device(id)
            ui_signals.selection.device.emit(None)

    def handle_connect_device(self, id: str):
        def on_result(ok: bool, err: str) -> None:
            if not ok:
                notifications.error.emit("Unable to connect to device", err)

        global_config.device_store.connect_device(id, on_result)

    def handle_disconnect_device(self, id: str):
        global_config.device_store.disconnect_device(id)

    def send_field_set(self, id: str, field: str):
        ui_signals.devices_req.set_field.emit(
            id, field, getattr(global_config.device_store.get(id).config, field)
        )

    def id_exists(self, id: str):
        return id in global_config.device_store.all()
