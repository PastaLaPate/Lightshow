from PySide6.QtCore import QObject

from lightshow.core.config import global_config
from lightshow.devices.types import DeviceTypeName
from lightshow.document.history import global_history
from lightshow.gui.utils import ui_signals


class DeviceController(QObject):
    def __init__(self) -> None:
        super().__init__(None)
        ui_signals.create_device.connect(self.handle_create_device)
        ui_signals.rename_device.connect(self.handle_rename_device)
        ui_signals.delete_device.connect(self.handle_delete_device)

        # global_config.device_store.device_added.connect(ui_signals.new_device) Handled via handle_create_device, to attribute a name
        global_config.device_store.device_renamed.connect(ui_signals.device_renamed)
        global_config.device_store.device_removed.connect(ui_signals.device_deleted)

    def handle_create_device(self, device_type: DeviceTypeName, name: str | None):
        with global_history.transaction("Create and rename device"):
            id = global_config.device_store.new_device(device_type)
            global_config.device_store.rename_device(
                id, name or f"Device {len(global_config.device_store.all()) + 1}"
            )
            ui_signals.new_device.emit(id)

    def handle_rename_device(self, id: str, new_name: str):
        if not self.id_exists(id) or new_name == "":
            return

        with global_history.transaction("Rename device"):
            global_config.device_store.rename_device(id, new_name)

    def handle_delete_device(self, id: str):
        if not self.id_exists(id):
            return

        with global_history.transaction("Delete device"):
            global_config.device_store.delete_device(id)
            ui_signals.device_selected.emit(None)

    def id_exists(self, id: str):
        return id in global_config.device_store.all()
