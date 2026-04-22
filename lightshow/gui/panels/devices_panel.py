from typing import List, Type

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from lightshow.devices import is_device_type
from lightshow.devices.device import Device
from lightshow.utils import Logger, global_config
from lightshow.utils.config import DeviceConfigType

from .base_panel import BasePanel

logger = Logger.for_class("DevicesPanel")


class DeviceListWidget(QListWidget):
    """QListWidget with Delete key support."""

    def __init__(self, on_delete_callback):
        super().__init__()
        self._on_delete = on_delete_callback

    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if e and e.key() == Qt.Key.Key_Delete:
            self._on_delete()
        else:
            super().keyPressEvent(e)


class DevicesPanel(BasePanel):
    """Panel for managing device list and additions."""

    def __init__(self, device_types: List[Type[Device]]):
        super().__init__()
        self.device_types = device_types
        self.device_listbox: DeviceListWidget | None = None
        self.device_type_combo: QComboBox | None = None

    def refresh_list(self):
        """Refresh the device listbox with current devices."""
        if self.device_listbox is not None:
            self.device_listbox.clear()
            for device_name in global_config.devices.keys():
                self.device_listbox.addItem(device_name)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the devices panel UI elements."""
        # Title
        title_label = QLabel("Devices")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Device listbox
        self.device_listbox = DeviceListWidget(self._delete_selected_device)
        self.device_listbox.setMaximumHeight(200)
        for device_name in global_config.devices.keys():
            self.device_listbox.addItem(device_name)
        self.device_listbox.itemSelectionChanged.connect(self._on_device_select)
        self.device_listbox.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_listbox.customContextMenuRequested.connect(self._show_context_menu)
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
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if current_item:
            device_name = current_item.text()
            self.trigger("device_selected", device_name)

    def _show_context_menu(self, pos):
        """Show right-click context menu on a list item."""
        if not self.device_listbox:
            return
        item = self.device_listbox.itemAt(pos)
        if not item:
            return

        menu = QMenu(self.device_listbox)

        duplicate_action = QAction("Duplicate", self.device_listbox)
        duplicate_action.triggered.connect(lambda: self._duplicate_device(item.text()))
        menu.addAction(duplicate_action)

        delete_action = QAction("Delete", self.device_listbox)
        delete_action.triggered.connect(self._delete_selected_device)
        menu.addAction(delete_action)

        menu.exec(self.device_listbox.mapToGlobal(pos))

    def _delete_selected_device(self):
        """Delete the currently selected device."""
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if not current_item:
            return
        device_id = current_item.text()
        if device_id in global_config.devices:
            del global_config.devices[device_id]
            logger.info(f"Deleted device: {device_id}")
            self.refresh_list()
            self.trigger("device_deleted", device_id)

    def _duplicate_device(self, device_id: str):
        """Duplicate an existing device with a new unique ID."""
        if device_id not in global_config.devices:
            return

        source_config = global_config.devices[device_id]

        # Find a unique ID for the duplicate
        base_id = f"{device_id}_copy"
        new_id = base_id
        counter = 1
        while new_id in global_config.devices:
            new_id = f"{base_id}_{counter}"
            counter += 1

        # Deep-copy the config
        global_config.devices[new_id] = DeviceConfigType(
            {
                "type": source_config["type"],
                "props": source_config.get("props", {}).copy(),
            }
        )

        logger.info(f"Duplicated device '{device_id}' as '{new_id}'")
        self.refresh_list()
        self._select_device_by_id(new_id)
        self.trigger("device_added", new_id)

    def _add_device_callback(self):
        """Handle adding a new device."""
        if not self.device_type_combo:
            return
        device_type_name = self.device_type_combo.currentText()
        device_type = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        if device_type:
            device_count = len(global_config.devices)
            device_id = f"{device_type_name}_{device_count}"
            if is_device_type(device_type_name):
                global_config.devices[device_id] = DeviceConfigType(
                    {
                        "type": device_type_name,
                        "props": getattr(device_type, "DEFAULT_CONFIG", {}).copy(),
                    }
                )
            self.refresh_list()
            self._select_device_by_id(device_id)
            self.trigger("device_added", device_id)

    def _select_device_by_id(self, device_id: str):
        """Select a device in the listbox by its ID."""
        if not self.device_listbox:
            return
        for i in range(self.device_listbox.count()):
            item = self.device_listbox.item(i)
            if item and item.text() == device_id:
                self.device_listbox.setCurrentRow(i)
                return
