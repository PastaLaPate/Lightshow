from PyQt6.QtCore import QObject, pyqtSignal

from lightshow.devices.devices_types import DeviceTypeName


class UISignals(QObject):
    """Signals for thread-safe communication with UI."""

    finish_connection = pyqtSignal(str)
    show_error = pyqtSignal(str, str)
    show_info = pyqtSignal(str, str)
    connection_status_changed = pyqtSignal(str)
    streaming_status_changed = pyqtSignal(bool)

    create_device = pyqtSignal(
        DeviceTypeName, object
    )  # When new is clicked, DeviceType, name (optional)
    rename_device = pyqtSignal(str, str)  # id, new_name
    delete_device = pyqtSignal(str)  # id

    new_device = pyqtSignal(str)  # New device has been created, id
    device_renamed = pyqtSignal(str, str)  # id, new_name
    device_deleted = pyqtSignal(str)  # id


ui_signals = UISignals()
