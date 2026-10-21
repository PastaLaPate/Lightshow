from PySide6.QtCore import QObject, Signal

from lightshow.audio.types import AudioDevice
from lightshow.devices.status import DeviceStatus
from lightshow.devices.types import DeviceTypeName


class DeviceRequests(QObject):
    create = Signal(DeviceTypeName, object)  # type, name | None
    rename = Signal(str, str)
    delete = Signal(str)
    set_field = Signal(str, str, object)


class DeviceEvents(QObject):
    created = Signal(str)
    renamed = Signal(str, str)
    deleted = Signal(str)
    field_set = Signal(str, str, object)
    status_changed = Signal(str, DeviceStatus)
    selected = Signal(object)  # selection is UI state, see below
    connection_status_changed = Signal(str)
    finish_connection = Signal(str)


class AudioRequests(QObject):
    start_stream = Signal()
    stop_stream = Signal()
    set_device = Signal(AudioDevice)


class AudioEvents(QObject):
    streaming_status_changed = Signal(bool)


class DialogSignals(QObject):
    show_error = Signal(str, str)
    show_info = Signal(str, str)


class SettingsSignals(QObject):
    changed = Signal(dict)


class UISignals:
    """Plain namespace, no need for it to be a QObject."""

    def __init__(self):
        self.devices_req = DeviceRequests()
        self.devices = DeviceEvents()
        self.audio_req = AudioRequests()
        self.audio = AudioEvents()
        self.dialogs = DialogSignals()
        self.settings = SettingsSignals()


ui_signals = UISignals()
