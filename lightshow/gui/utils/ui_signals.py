from PySide6.QtCore import QObject, Signal

from lightshow.devices.devices_types import DeviceTypeName


class UISignals(QObject):
    """Signals for thread-safe communication with UI."""

    finish_connection = Signal(str)
    show_error = Signal(str, str)
    show_info = Signal(str, str)
    connection_status_changed = Signal(str)
    streaming_status_changed = Signal(bool)

    device_selected = Signal(object)  # id | None

    create_device = Signal(
        DeviceTypeName, object
    )  # When new is clicked, DeviceType, name (optional)
    rename_device = Signal(str, str)  # id, new_name
    delete_device = Signal(str)  # id

    new_device = Signal(str)  # New device has been created, id
    device_renamed = Signal(str, str)  # id, new_name
    device_deleted = Signal(str)  # id


ui_signals = UISignals()
