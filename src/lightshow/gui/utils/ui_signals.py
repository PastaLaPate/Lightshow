from PySide6.QtCore import QObject, Signal

from lightshow.audio.types import AudioDevice
from lightshow.devices.types import DeviceTypeName


class UISignals(QObject):
    """Signals for thread-safe communication with UI."""

    settings_changed = Signal(dict)  # Dict of changed settings

    finish_connection = Signal(str)
    show_error = Signal(str, str)
    show_info = Signal(str, str)
    connection_status_changed = Signal(str)

    streaming_status_changed = Signal(bool)  # current stream status: True == streaming
    start_stream = Signal()
    stop_stream = Signal()
    set_audio_device = Signal(AudioDevice)  # AudioDevice

    device_selected = Signal(object)  # id | None

    create_device = Signal(
        DeviceTypeName, DeviceTypeName
    )  # When new is clicked, DeviceType, name (optional)
    set_field = Signal(str, str, object)  # device_id, field, value
    rename_device = Signal(str, str)  # id, new_name
    delete_device = Signal(str)  # id

    new_device = Signal(str)  # New device has been created, id
    field_set = Signal(str, str, object)  # device_id, field, new_value
    device_renamed = Signal(str, str)  # id, new_name
    device_deleted = Signal(str)  # id


ui_signals = UISignals()
