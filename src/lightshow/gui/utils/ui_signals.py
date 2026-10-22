from PySide6.QtCore import QObject, Signal

from lightshow.audio.types import AudioDevice
from lightshow.devices.status import DeviceStatus
from lightshow.devices.types import DeviceTypeName


class DeviceRequests(QObject):
    create = Signal(DeviceTypeName, object)  # type, name | None
    rename = Signal(str, str)  # id, new_name
    delete = Signal(str)  # id
    set_field = Signal(str, str, object)  # id, name, value


class DeviceEvents(QObject):
    created = Signal(str)  # id
    renamed = Signal(str, str)  # id, new_name
    deleted = Signal(str)  # id
    field_set = Signal(str, str, object)  # id, name, value
    status_changed = Signal(str, DeviceStatus)  # id, new_status
    selected = Signal(object)
    connection_status_changed = Signal(str)  # new_status


class AudioRequests(QObject):
    start_stream = Signal()
    stop_stream = Signal()
    set_device = Signal(AudioDevice)  # device


class AudioEvents(QObject):
    streaming_status_changed = Signal(
        bool
    )  # True if stream is started False if stopped


class DialogSignals(QObject):
    show_error = Signal(str, str)  # Title, content
    show_info = Signal(str, str)  # Title, content


class SettingsSignals(QObject):
    changed = Signal(dict)  # Dict of changed settings


class UISignals:
    def __init__(self):
        self.devices_req = DeviceRequests()
        self.devices = DeviceEvents()
        self.audio_req = AudioRequests()
        self.audio = AudioEvents()
        self.dialogs = DialogSignals()
        self.settings = SettingsSignals()


ui_signals = UISignals()
