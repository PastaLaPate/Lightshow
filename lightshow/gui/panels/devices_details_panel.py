from enum import IntEnum, auto

from PySide6.QtCore import Property, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from lightshow.devices.device import Device
from lightshow.gui.components.editable_label import EditableLabel
from lightshow.gui.components.status_circle import StatusCircle
from lightshow.gui.utils import ui_signals

from .base_panel import BasePanel


class DeviceStatus(IntEnum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()


class DeviceHeader(QWidget):
    device_renamed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._status = DeviceStatus.DISCONNECTED

        layout = QHBoxLayout()

        self._status_circle = StatusCircle()
        self._status_circle.setFixedHeight(16)

        self._name_label = EditableLabel("Test")
        self._name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._name_label.text_changed.connect(self.device_renamed)

        self._type_label = QLabel("Moving Head")

        layout.addWidget(self._status_circle)
        layout.addWidget(self._name_label)
        layout.addStretch()
        layout.addWidget(self._type_label)
        self.setLayout(layout)

    def get_status(self) -> DeviceStatus:
        return self._status

    def set_status(self, status: DeviceStatus):
        self._status = status
        match status:
            case DeviceStatus.DISCONNECTED:
                self._status_circle.color = Qt.GlobalColor.red
                self._status_circle.set_pulsing(False)
            case DeviceStatus.CONNECTING:
                self._status_circle.color = Qt.GlobalColor.blue
                self._status_circle.set_pulsing(True)
            case DeviceStatus.CONNECTED:
                self._status_circle.color = Qt.GlobalColor.green
                self._status_circle.set_pulsing(False)

    def get_device_name(self) -> str:
        return self._name_label.text()

    def set_device_name(self, device_name: str):
        self._name_label.setText(device_name)

    def get_device_type(self) -> str:
        return self._type_label.text()

    def set_device_type(self, device_type: str):
        self._type_label.setText(device_type)

    device_name = Property(
        str, fget=get_device_name, fset=set_device_name, notify=device_renamed
    )


class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()
        self.device_types: list[type[Device]] = device_types
        self.stacked_layout: QStackedLayout | None = None

        ui_signals.device_selected.connect(self.device_selected)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the device details panel UI elements."""
        # Title
        title_label = QLabel("Device Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Placeholder
        self.placeholder_label = QLabel("Select a device to see its details.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.stacked_layout = QStackedLayout()
        self.stacked_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stacked_layout.addWidget(self.placeholder_label)

        layout.addWidget(title_label)
        layout.addLayout(self.stacked_layout)
        layout.addWidget(DeviceHeader())

    def device_selected(self, device_id: str | None):
        assert self.stacked_layout is not None
        print(device_id)
        if device_id:
            self.stacked_layout.setCurrentIndex(0)
        else:
            self.stacked_layout.setCurrentIndex(1)
