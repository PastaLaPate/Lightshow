from lightshow.core.config import global_config
from lightshow.devices.types import DeviceTypeName
from lightshow.document.actions.action import Action


class NewDeviceAction(Action):
    def __init__(self, id: str, index: int, device_type: DeviceTypeName):
        super().__init__(id, index)
        self.device_type = device_type

    def apply(self):
        global_config.device_store.new_device(self.device_type)
