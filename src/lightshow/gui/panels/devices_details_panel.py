from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from lightshow.core.config import global_config
from lightshow.devices.device import Device
from lightshow.devices.registry import DEVICE_CLASSES
from lightshow.devices.status import DeviceStatus
from lightshow.devices.store import DeviceEntry
from lightshow.gui.components.badge import Badge
from lightshow.gui.components.editable_label import EditableLabel
from lightshow.gui.components.status_circle import StatusCircle
from lightshow.gui.theme import style
from lightshow.gui.utils import ui_signals
from lightshow.gui.utils.form_builder import ModelForm, RuntimeView

from .base_panel import BasePanel


class DeviceHeader(QWidget):
    device_renamed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._status = DeviceStatus.DISCONNECTED

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_circle = StatusCircle()
        self.status_circle.setFixedHeight(16)

        self.device_name = EditableLabel("")
        style.mark(self.device_name, "heading")
        self.device_name.text_changed.connect(self.device_renamed)

        self.device_type = Badge("Moving Head", QColor(100, 100, 100))

        layout.addWidget(self.status_circle)
        layout.addWidget(self.device_name)
        layout.addStretch()
        layout.addWidget(self.device_type)
        self.setLayout(layout)

    def get_status(self) -> DeviceStatus:
        return self._status

    def set_status(self, status: DeviceStatus):
        self._status = status
        match status:
            case DeviceStatus.DISCONNECTED:
                self.status_circle.color = Qt.GlobalColor.red
                self.status_circle.set_pulsing(False)
            case DeviceStatus.CONNECTING:
                self.status_circle.color = Qt.GlobalColor.blue
                self.status_circle.set_pulsing(True)
            case DeviceStatus.CONNECTED:
                self.status_circle.color = Qt.GlobalColor.green
                self.status_circle.set_pulsing(False)

    def get_device_name(self) -> str:
        return self.device_name.text()

    def set_device_name(self, device_name: str):
        self.device_name.setText(device_name)

    def set_badge_color(self, color: QColor) -> None:
        self.device_type.color = color

    def get_device_type(self) -> str:
        return self.device_type.text()

    def set_device_type(self, device_type: str):
        self.device_type.setText(device_type)


class DeviceProps(
    QWidget,
):
    field_changed = Signal(str, object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.form = ModelForm()
        self.form.field_changed.connect(self.field_changed)

        layout.addWidget(self.form)

        self.setLayout(layout)

    def set_connected(self, connected: bool):
        self.form.set_connected(connected)

    def render_device(self, entry: DeviceEntry):
        self.form.construct(DEVICE_CLASSES[entry.type_name].CONFIG_SCHEMA, entry.config)


class DeviceRuntimeProps(QWidget):
    _change_field = Signal(str, object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._current_device: str | None = None
        self._unsubscribers: list[Callable[[], None]] = []

        self.view = RuntimeView()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setVisible(False)

        self._change_field.connect(self.view.set_value)
        unsubs = self._unsubscribers
        self.destroyed.connect(lambda *_: [u() for u in unsubs])

    def clear(self):
        [
            unsubscribe() for unsubscribe in self._unsubscribers
        ]  # List comprehension not because we should but because we can
        self._unsubscribers.clear()
        self.view.clear()
        self._current_device = None
        self.setVisible(False)

    def track_device(self, device_id: str):
        if device_id == self._current_device:
            return
        self.clear()
        entry = global_config.device_store.get(device_id)
        if entry.status != DeviceStatus.CONNECTED or entry._device is None:
            return
        device = entry.device
        if device.RUNTIME_SCHEMA is None or device.runtime is None:
            return

        self._current_device = device_id
        self.view.build(device.RUNTIME_SCHEMA, device.runtime)
        self.setVisible(True)
        self._unsubscribers.append(
            device.runtime.subscribe(
                lambda field, _old, new: self._change_field.emit(field, new)
            )
        )


class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()

        self.device_types: list[type[Device]] = device_types
        self.stacked_layout: QStackedLayout | None = None
        self.current_device: str | None = None
        self.current_status: DeviceStatus = DeviceStatus.DISCONNECTED

        self._connect_button_messages_dict: dict[DeviceStatus, str] = {
            DeviceStatus.DISCONNECTED: "Connect to device",
            DeviceStatus.CONNECTING: "Connecting to device",
            DeviceStatus.CONNECTED: "Disconnect from device",
        }

        ui_signals.devices.selected.connect(self._on_device_selected)
        ui_signals.devices.renamed.connect(self._on_device_renamed)
        ui_signals.devices.status_changed.connect(self._on_device_status_changed)
        ui_signals.devices.field_set.connect(self.set_field)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the device details panel UI elements."""
        style.mark(self, "panel")
        # Title
        title_label = QLabel("Device Details")
        style.mark(title_label, "heading")
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Placeholder
        self.placeholder_label = QLabel("Select a device to see its details.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        props_widget = QWidget()
        props_widget.setContentsMargins(0, 0, 0, 0)
        props_layout = QVBoxLayout()
        props_layout.setContentsMargins(0, 0, 0, 0)

        self.device_header = DeviceHeader()
        self.device_header.device_renamed.connect(self.rename_device)

        self.device_props = DeviceProps()
        self.device_props.field_changed.connect(self._on_field_changed)

        self.device_runtime = DeviceRuntimeProps()

        self.connect_btn = QPushButton()
        self.connect_btn.clicked.connect(self.connect_device)

        props_layout.addWidget(self.device_header)
        props_layout.addWidget(self.device_props)
        props_layout.addWidget(self.device_runtime)
        props_layout.addWidget(self.connect_btn)

        props_widget.setLayout(props_layout)

        self.stacked_layout = QStackedLayout()
        self.stacked_layout.addWidget(props_widget)
        self.stacked_layout.addWidget(self.placeholder_label)
        self.stacked_layout.setCurrentIndex(1)

        layout.addWidget(title_label)
        layout.addLayout(self.stacked_layout, 1)

    def update_status(self, new_status: DeviceStatus):
        self.current_status = new_status
        self.connect_btn.setText(self._connect_button_messages_dict[new_status])
        self.connect_btn.setEnabled(new_status != DeviceStatus.CONNECTING)
        self.device_props.set_connected(new_status != DeviceStatus.DISCONNECTED)

    def rename_device(self, new_name: str):
        if self.current_device is not None:
            ui_signals.devices_req.rename.emit(self.current_device, new_name)

    def connect_device(self):
        match self.current_status:
            case DeviceStatus.DISCONNECTED:
                ui_signals.devices_req.connect_.emit(self.current_device)
            case DeviceStatus.CONNECTED:
                ui_signals.devices_req.disconnect_.emit(self.current_device)

    def set_field(self, id: str, name: str, value: Any):
        if self.current_device != id:
            return
        if name == "name" or name == "id":  # Name and ID arent in the form
            return
        self.device_props.form.set_field(name, value)

    def _on_device_renamed(self, device_id: str, new_name: str):
        if device_id == self.current_device:
            self.device_header.set_device_name(new_name)

    def _on_device_status_changed(self, device_id: str, new_status: DeviceStatus):
        if device_id == self.current_device:
            self.device_header.set_status(new_status)
            self.update_status(new_status)
            if new_status == DeviceStatus.CONNECTED:
                self.device_runtime.track_device(device_id)
            else:
                self.device_runtime.clear()

    def _on_field_changed(self, name: str, value: Any):
        if self.current_device is not None:
            ui_signals.devices_req.set_field.emit(self.current_device, name, value)

    def _on_device_selected(self, device_id: str | None):
        assert self.stacked_layout is not None
        self.current_device = device_id
        if device_id is not None:
            self.stacked_layout.setCurrentIndex(0)
            entry = global_config.device_store.get(device_id)
            self.device_header.set_device_name(entry.config.name)
            self.device_header.set_device_type(entry.type_name)
            self.device_header.set_badge_color(
                QColor(DEVICE_CLASSES[entry.type_name].BADGE_COLOR)
            )
            self.device_header.set_status(entry.status)
            self.device_props.render_device(entry)
            self.update_status(entry.status)

            if entry.status == DeviceStatus.CONNECTED:
                self.device_runtime.track_device(device_id)
            else:
                self.device_runtime.clear()
        else:
            self.stacked_layout.setCurrentIndex(1)
