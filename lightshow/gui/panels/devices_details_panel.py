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
from lightshow.utils import Config, live_devices
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
        # Showed props (runtime/debug info) UI
        self.showed_props_layout = None
        self.showed_prop_labels: dict[str, QLabel] = {}
        self._current_live_device = None

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

        # Runtime / debug properties shown by the live device
        self.showed_props_layout = QVBoxLayout()
        self.details_layout.addLayout(self.showed_props_layout)

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
        if self.placeholder_label and self.details_layout:
            self.placeholder_label.setVisible(not visible)
            for i in range(self.details_layout.count()):
                item = self.details_layout.itemAt(i)
                if not item:
                    continue
                widget = item.widget()
                layout = item.layout()
                if widget:
                    widget.setVisible(visible)
                elif layout:
                    for j in range(layout.count()):
                        sub_item = layout.itemAt(j)
                        if not sub_item:
                            continue
                        sub_item_widget = sub_item.widget()
                        if sub_item_widget:
                            sub_item_widget.setVisible(visible)

    def show_for(self, device_id):
        """Display details for a specific device."""
        if not device_id or device_id not in self.config.devices:
            self._set_details_visible(False)
            self.selected_device_id = None
            return

        selected_device_obj = self.config.devices[device_id]
        self.selected_device_id = device_id
        self._set_details_visible(True)

        if (
            not self.device_name_input
            or not self.device_type_label
            or not self.progress_bar
            or not self.connect_button
            or not self.status_label
        ):
            return

        self.device_name_input.setText(device_id)
        self.device_type_label.setText(f"Type: {selected_device_obj['type']}")

        # Populate editable properties for this device type
        # Clear existing prop widgets
        self.prop_widgets.clear()
        if self.props_layout:
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
                                if not si:
                                    return
                                w = si.widget()
                                if si and w:
                                    w.deleteLater()

        # Find device type class
        device_type_name = selected_device_obj.get("type")
        device_type_cls = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        props = selected_device_obj.get("props", {})
        if not isinstance(self.props_layout, QVBoxLayout):
            return

        # Populate showed (runtime) properties section
        # Clear existing showed props widgets
        self.showed_prop_labels.clear()
        if self.showed_props_layout:
            while self.showed_props_layout.count():
                item = self.showed_props_layout.takeAt(0)
                if item:
                    w = item.widget()
                    if w:
                        w.deleteLater()
                    else:
                        sub_layout = item.layout()
                        if sub_layout:
                            while sub_layout.count():
                                si = sub_layout.takeAt(0)
                                if not si:
                                    break
                                w = si.widget()
                                if w:
                                    w.deleteLater()

        device_type_name = selected_device_obj.get("type")
        device_type_cls = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )

        # If there is a live device instance, attach a showed_props listener
        # First detach listener from previous live device (if any)
        try:
            if self._current_live_device and hasattr(
                self._current_live_device, "set_showed_props_listener"
            ):
                self._current_live_device.set_showed_props_listener(None)
        except Exception:
            pass
        self._current_live_device = None

        # If device class defines SHOWED_PROPS, create labels for them
        if device_type_cls and hasattr(device_type_cls, "SHOWED_PROPS"):
            for pname in getattr(device_type_cls, "SHOWED_PROPS", []):
                pname: str = pname
                formatted = pname.replace("_", " ").title()
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{formatted}:"))
                value_label = QLabel("")
                # initialize from saved props when available
                try:
                    initial = props.get(pname, "")
                except Exception:
                    initial = ""
                value_label.setText(str(initial))
                row.addWidget(value_label)
                self.showed_props_layout.addLayout(row)
                self.showed_prop_labels[pname] = value_label

        # Attach live device listener if available
        live_dev = None
        try:
            if device_id in live_devices:
                live_dev = live_devices[device_id]
        except Exception:
            live_dev = None

        if live_dev:
            # initialize/override labels from current live device attributes
            for pname, lab in self.showed_prop_labels.items():
                try:
                    val = getattr(live_dev, pname, None)
                    if val is None:
                        # fallback to saved props if live attribute missing
                        val = props.get(pname, "")
                except Exception:
                    val = props.get(pname, "")
                lab.setText(str(val))

            # register listener to update labels from device
            def _on_update(prop, value):
                lab = self.showed_prop_labels.get(prop)
                if lab:
                    lab.setText(str(value))

            try:
                if hasattr(live_dev, "set_showed_props_listener"):
                    live_dev.set_showed_props_listener(_on_update)
                    self._current_live_device = live_dev
                    # Trigger an immediate update from the device in case it already
                    # has values to report (ensures UI shows udp_address etc.)
                    try:
                        live_dev.showed_props_update()
                    except Exception:
                        pass
            except Exception:
                pass

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
        if not self.connect_button or not self.status_label:
            return
        if connected:
            self.connect_button.setText("Disconnect")
            self.status_label.setText("Status: Connected")
        else:
            self.connect_button.setText("Connect")
            self.status_label.setText("Status: Disconnected")

    def set_connecting(self, connecting: bool):
        """Update connecting state."""
        if not self.progress_bar or not self.connect_button or not self.status_label:
            return
        self.progress_bar.setVisible(connecting)
        self.connect_button.setEnabled(not connecting)
        if connecting:
            self.connect_button.setText("Connecting")
            self.status_label.setText("Status: Connecting...")

    def set_status(self, status: str):
        """Set the status label text."""
        if not self.status_label:
            return
        self.status_label.setText(status)

    def clear(self):
        """Clear the details panel."""
        # detach showed props listener if set
        try:
            if self._current_live_device and hasattr(
                self._current_live_device, "set_showed_props_listener"
            ):
                self._current_live_device.set_showed_props_listener(None)
        except Exception:
            pass
        self._current_live_device = None

        self._set_details_visible(False)
        self.selected_device_id = None

    def _connect_device_callback(self):
        """Handle connect button click."""
        self.trigger("connect_clicked", self.selected_device_id)

    def _delete_device(self):
        """Handle delete button click."""
        self.trigger("delete_clicked", self.selected_device_id)
