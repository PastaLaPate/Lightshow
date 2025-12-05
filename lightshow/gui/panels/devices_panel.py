from typing import List, Type

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QComboBox,
    QPushButton,
)

from .base_panel import BasePanel
from lightshow.utils.config import Config
from lightshow.devices.device import Device


class DevicesPanel(BasePanel):
    """Panel for managing device list and additions."""

    def __init__(self, config: Config, device_types: List[Type[Device]]):
        super().__init__()
        self.config = config
        self.device_types = device_types
        self.device_listbox = None
        self.device_type_combo = None

    def refresh_list(self):
        """Refresh the device listbox with current devices."""
        if self.device_listbox:
            self.device_listbox.clear()
            for device_name in self.config.devices.keys():
                self.device_listbox.addItem(device_name)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the devices panel UI elements."""
        # Title
        title_label = QLabel("Devices")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Device listbox
        self.device_listbox = QListWidget()
        self.device_listbox.setMaximumHeight(200)
        for device_name in self.config.devices.keys():
            self.device_listbox.addItem(device_name)
        self.device_listbox.itemSelectionChanged.connect(self._on_device_select)
        layout.addWidget(self.device_listbox)

        # Add device controls
        add_layout = QHBoxLayout()

        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(
            [dt.DEVICE_TYPE_NAME for dt in self.device_types]
        )
        add_layout.addWidget(self.device_type_combo)

        add_button = QPushButton("Add Device")
        add_button.clicked.connect(self._add_device_callback)
        add_layout.addWidget(add_button)

        layout.addLayout(add_layout)
        layout.addStretch()

    def _on_device_select(self):
        """Handle device selection from listbox."""
        current_item = self.device_listbox.currentItem()
        if current_item:
            device_name = current_item.text()
            self.trigger("device_selected", device_name)

    def _add_device_callback(self):
        """Handle adding a new device."""
        device_type_name = self.device_type_combo.currentText()
        device_type = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        if device_type:
            # Create a default device config
            device_count = len(self.config.devices)
            device_id = f"{device_type_name}_{device_count}"
            self.config.devices[device_id] = {
                "type": device_type_name,
                "props": getattr(device_type, "DEFAULT_CONFIG", {}).copy(),
            }
            self.refresh_list()
            # Select the newly added device in the list so details show up
            if self.device_listbox:
                items = [
                    self.device_listbox.item(i).text()
                    for i in range(self.device_listbox.count())
                ]
                try:
                    idx = items.index(device_id)
                    self.device_listbox.setCurrentRow(idx)
                except ValueError:
                    pass
            self.trigger("device_added", device_id)
