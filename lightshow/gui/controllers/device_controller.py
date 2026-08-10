from uuid import uuid4

from PyQt6.QtCore import QObject

from lightshow.devices.device import BaseDeviceSettings
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.gui.utils import ui_signals
from lightshow.utils import global_config, live_devices
from lightshow.utils.config import DeviceConfigType


class DeviceController(QObject):
    def __init__(self) -> None:
        super().__init__(None)
        ui_signals.create_device.connect(self.handle_create_device)
        ui_signals.rename_device.connect(self.handle_rename_device)
        ui_signals.delete_device.connect(self.handle_delete_device)

    def handle_create_device(self, device_type: DeviceTypeName, name: str | None):
        id = str(uuid4())
        global_config.devices[id] = DeviceConfigType(
            type=device_type,
            props=BaseDeviceSettings(
                id=id, name=name or f"Device {len(global_config.devices) + 1}"
            ).model_dump(),
        )
        ui_signals.new_device.emit(id)

    def handle_rename_device(self, id: str, new_name: str):
        if not self.id_exists(id) or new_name == "":
            return

        if id in live_devices:  # When connected, the instance becomes truth
            live_devices[id].name = new_name
        else:
            global_config.devices[id]["props"]["name"] = new_name
        ui_signals.device_renamed.emit(id, new_name)

    def handle_delete_device(self, id: str):
        print("uhh")
        if not self.id_exists(id):
            return

        if id in live_devices:
            return
        else:
            del global_config.devices[id]
            ui_signals.device_deleted.emit(id)

    def id_exists(self, id: str):
        return id in global_config.devices or id in live_devices
