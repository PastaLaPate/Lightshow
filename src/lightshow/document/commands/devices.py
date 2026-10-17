from lightshow.core.config import global_config
from lightshow.devices.types import DeviceTypeName
from lightshow.document.history import global_history


def create_device(self, type_name: DeviceTypeName):
    with global_history.transaction("Creating Device"):
        global_config.device_store.new_device(type_name)


def rename_device(self, device_id: str, new_name: str):
    with global_history.transaction("Rename Device"):
        global_config.device_store.update(device_id, "name", new_name)
