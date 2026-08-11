from functools import partial

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from lightshow.devices.device import Device
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.gui.utils import ui_signals
from lightshow.logger import Logger
from lightshow.utils import global_config

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

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()
        self.device_types = device_types
        self.device_listbox: DeviceListWidget | None = None
        self.device_type_combo: QComboBox | None = None

        ui_signals.new_device.connect(self._device_created)
        ui_signals.device_renamed.connect(self.refresh_list)
        ui_signals.device_deleted.connect(self.refresh_list)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the devices panel UI elements."""
        title_label = QLabel("Devices")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        self.device_listbox = DeviceListWidget(self._delete_selected_device)
        self.device_listbox.setMaximumHeight(200)
        self.refresh_list()
        self.device_listbox.itemSelectionChanged.connect(
            self._on_device_select
        )
        self.device_listbox.itemChanged.connect(self._on_item_renamed)
        self.device_listbox.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.device_listbox.customContextMenuRequested.connect(
            self._show_selected_context_menu
        )
        layout.addWidget(self.device_listbox)

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

    def refresh_list(self, *args):
        """Refresh the device listbox with current devices."""
        if self.device_listbox is not None:
            self.device_listbox.clear()
            for id, config in global_config.devices.items():
                item = QListWidgetItem(config["props"]["name"])
                item.setData(Qt.ItemDataRole.UserRole, id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.device_listbox.addItem(item)

    def _device_created(self, id: str):
        self.refresh_list()
        item = self._select_device_by_id(id)
        if item and self.device_listbox is not None:
            self.device_listbox.editItem(item)

    def _on_device_select(self):
        """Handle device selection from listbox."""
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if current_item:
            device_name = current_item.text()
            self.trigger("device_selected", device_name)

    def _on_item_renamed(self, item: QListWidgetItem):
        device_id = item.data(Qt.ItemDataRole.UserRole)
        new_name = item.text().strip()

        if (
            not device_id
            or not new_name
            or device_id not in global_config.devices
        ):
            return

        ui_signals.rename_device.emit(device_id, new_name)

    def _add_device_callback(self):
        """Handle adding a new device."""
        if not self.device_type_combo:
            return
        device_type_name = self.device_type_combo.currentText()
        device_type: DeviceTypeName = next(
            (t for t in list(DeviceTypeName) if t.value == device_type_name),
            DeviceTypeName.MOVING_HEAD,
        )
        ui_signals.create_device.emit(device_type, "")

    def _delete_selected_device(self):
        """Delete the currently selected device."""
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if not current_item:
            return
        device_id = current_item.data(Qt.ItemDataRole.UserRole)
        if device_id in global_config.devices:
            ui_signals.delete_device.emit(device_id)

    def _duplicate_device(self, device_id: str):
        """Duplicate an existing device with a new unique ID."""
        if device_id not in global_config.devices:
            return

        source_config = global_config.devices[device_id]

    def _show_selected_context_menu(self, pos):
        """Show right-click context menu on a list item."""
        if self.device_listbox is None:
            return
        item = self.device_listbox.itemAt(pos)
        if not item:
            self._show_context_menu(pos)
            return

        menu = QMenu(self.device_listbox)

        duplicate_action = QAction("Duplicate", self.device_listbox)
        duplicate_action.triggered.connect(
            lambda: self._duplicate_device(item.data(Qt.ItemDataRole.UserRole))
        )
        # menu.addAction(duplicate_action)

        delete_action = QAction("Delete", self.device_listbox)
        delete_action.triggered.connect(self._delete_selected_device)
        menu.addAction(delete_action)

        menu.exec(self.device_listbox.mapToGlobal(pos))

    def _show_context_menu(self, pos):
        """Show right-click context menu on device list."""
        if self.device_listbox is None:
            return

        menu = QMenu(self.device_listbox)

        new_action = QMenu("New", self.device_listbox)
        for device in list(DeviceTypeName):
            new_device_action = QAction(
                device.value, parent=self.device_listbox
            )
            new_device_action.triggered.connect(
                partial(ui_signals.create_device.emit, device, "")
            )
            new_action.addAction(new_device_action)
        menu.addMenu(new_action)

        menu.exec(self.device_listbox.mapToGlobal(pos))

    def _select_device_by_id(self, device_id: str) -> QListWidgetItem | None:
        """Select a device in the listbox by its ID."""
        if not self.device_listbox:
            return
        for i in range(self.device_listbox.count()):
            item = self.device_listbox.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == device_id:
                self.device_listbox.setCurrentItem(item)
                return item
