from PySide6.QtCore import QObject, Signal

from lightshow.audio.types import AudioDevice
from lightshow.devices.types import DeviceTypeName, PacketData


class DeviceRequests(QObject):
    create = Signal(DeviceTypeName, object)  # type, name | None
    duplicate = Signal(str)  # device_id to dup
    rename = Signal(str, str)  # id, new_name
    delete = Signal(str)  # id
    set_field = Signal(str, str, object)  # id, name, value

    connect_ = Signal(str)
    disconnect_ = Signal(str)
    send_packet = Signal(PacketData)


class AudioRequests(QObject):
    start_stream = Signal()
    stop_stream = Signal()
    set_device = Signal(AudioDevice)  # device


class SelectionSignals(QObject):
    device = Signal(object)


class SettingsSignals(QObject):
    changed = Signal(dict)


class UISignals:
    def __init__(self):
        self.devices_req = DeviceRequests()
        self.audio_req = AudioRequests()
        self.selection = SelectionSignals()
        self.settings = SettingsSignals()


ui_signals = UISignals()
