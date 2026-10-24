from PySide6.QtCore import QObject, Signal

from lightshow.devices.types import DeviceStatus


class DeviceEvents(QObject):
    created = Signal(str)  # id
    renamed = Signal(str, str)  # id, new_name
    deleted = Signal(str)  # id
    field_set = Signal(str, str, object)  # id, name, value
    status_changed = Signal(str, DeviceStatus)


device_events = DeviceEvents()
