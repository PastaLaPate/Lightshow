from typing import List, Type

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QProgressBar,
)

from .base_panel import BasePanel
from lightshow.utils.config import Config, live_devices
from lightshow.devices.device import Device


class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""

    def __init__(self, config: Config, device_types: List[Type[Device]]):
        super().__init__()
        self.config = config
        self.device_types = device_types
        self.selected_device_id = None

        # UI Elements
        self.device_name_input = None
        self.device_type_label = None
        self.props_layout = None
        self.prop_widgets = {}
        self.connect_button = None
        self.delete_button = None
        self.status_label = None
        self.progress_bar = None
        self.details_layout = None
        self.placeholder_label = None

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the device details panel UI elements."""
        # Title
        title_label = QLabel("Device Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Placeholder
        self.placeholder_label = QLabel("Select a device to see its details.")
        layout.addWidget(self.placeholder_label)

        # Details group (hidden by default)
        self.details_layout = QVBoxLayout()

        # Device name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Device Name:"))
        self.device_name_input = QLineEdit()
        self.device_name_input.setReadOnly(True)
        name_layout.addWidget(self.device_name_input)
        self.details_layout.addLayout(name_layout)

        # Device type
        self.device_type_label = QLabel("Type: -")
        self.details_layout.addWidget(self.device_type_label)

        # Editable properties area (populated dynamically)
        self.props_layout = QVBoxLayout()
        self.details_layout.addLayout(self.props_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.details_layout.addWidget(separator)

        # Control buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect_device_callback)
        button_layout.addWidget(self.connect_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Makes it animate
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._delete_device)
        button_layout.addWidget(self.delete_button)

        self.details_layout.addLayout(button_layout)

        # Status
        self.status_label = QLabel("Status: Disconnected")
        self.details_layout.addWidget(self.status_label)

        self.details_layout.addStretch()
        layout.addLayout(self.details_layout)

        # Hide details by default
        self._set_details_visible(False)

    def _set_details_visible(self, visible):
        """Toggle visibility of details."""
        self.placeholder_label.setVisible(not visible)
        for i in range(self.details_layout.count()):
            item = self.details_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(visible)
            elif item and item.layout():
                for j in range(item.layout().count()):
                    sub_item = item.layout().itemAt(j)
                    if sub_item and sub_item.widget():
                        sub_item.widget().setVisible(visible)

    def show_for(self, device_id):
        """Display details for a specific device."""
        if not device_id or device_id not in self.config.devices:
            self._set_details_visible(False)
            self.selected_device_id = None
            return

        selected_device_obj = self.config.devices[device_id]
        self.selected_device_id = device_id
        self._set_details_visible(True)

        self.device_name_input.setText(device_id)
        self.device_type_label.setText(f"Type: {selected_device_obj['type']}")

        # Populate editable properties for this device type
        # Clear existing prop widgets
        self.prop_widgets.clear()
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()
                else:
                    # if it's a layout, clear its children
                    sub_layout = item.layout()
                    if sub_layout:
                        while sub_layout.count():
                            si = sub_layout.takeAt(0)
                            if si and si.widget():
                                si.widget().deleteLater()

        # Find device type class
        device_type_name = selected_device_obj.get("type")
        device_type_cls = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        props = selected_device_obj.get("props", {})
        if device_type_cls and hasattr(device_type_cls, "EDITABLE_PROPS"):
            for prop_name, prop_type in getattr(device_type_cls, "EDITABLE_PROPS", []):
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{prop_name}:"))
                editor = QLineEdit()
                editor.setText(str(props.get(prop_name, "")))

                def make_handler(did, pname, ptype, edt):
                    def handler():
                        val = edt.text()
                        # attempt to cast to declared type
                        try:
                            casted = ptype(val)
                        except Exception:
                            casted = val
                        self.config.devices[did]["props"][pname] = casted

                    return handler

                editor.editingFinished.connect(
                    make_handler(device_id, prop_name, prop_type, editor)
                )
                row.addWidget(editor)
                self.props_layout.addLayout(row)
                self.prop_widgets[prop_name] = editor

        # Update connection status UI
        self.progress_bar.setVisible(False)
        self.connect_button.setEnabled(True)
        if device_id in live_devices and live_devices[device_id].ready:
            self.connect_button.setText("Disconnect")
            self.status_label.setText("Status: Connected")
        elif device_id in live_devices and not live_devices[device_id].ready:
            self.connect_button.setText("Connecting")
            self.connect_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Status: Connecting...")
        else:
            self.connect_button.setText("Connect")
            self.status_label.setText("Status: Disconnected")

    def set_connected(self, connected: bool):
        """Update connected state."""
        if connected:
            self.connect_button.setText("Disconnect")
            self.status_label.setText("Status: Connected")
        else:
            self.connect_button.setText("Connect")
            self.status_label.setText("Status: Disconnected")

    def set_connecting(self, connecting: bool):
        """Update connecting state."""
        self.progress_bar.setVisible(connecting)
        self.connect_button.setEnabled(not connecting)
        if connecting:
            self.connect_button.setText("Connecting")
            self.status_label.setText("Status: Connecting...")

    def set_status(self, status: str):
        """Set the status label text."""
        self.status_label.setText(status)

    def clear(self):
        """Clear the details panel."""
        self._set_details_visible(False)
        self.selected_device_id = None

    def _connect_device_callback(self):
        """Handle connect button click."""
        self.trigger("connect_clicked", self.selected_device_id)

    def _delete_device(self):
        """Handle delete button click."""
        self.trigger("delete_clicked", self.selected_device_id)
