from functools import partial

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from lightshow.core.config import global_config
from lightshow.core.logger import Logger
from lightshow.devices.device import Device
from lightshow.devices.events import device_events
from lightshow.devices.types import DeviceTypeName
from lightshow.gui.components.badge import Badge
from lightshow.gui.components.editable_label import EditableLabel
from lightshow.gui.theme import style
from lightshow.gui.utils import ui_signals

from .base_panel import BasePanel

logger = Logger.for_class("DevicesPanel")


class DeviceListWidget(QListWidget):
    """QListWidget with Delete key support."""

    def __init__(self, on_delete_callback):
        super().__init__()
        self._on_delete = on_delete_callback

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e and e.key() == Qt.Key.Key_Delete:
            self._on_delete()
        else:
            super().keyPressEvent(e)


class FullRectDelegate(QStyledItemDelegate):
    """Row widgets get exactly the item rect (the default would inset them by the item padding)."""

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)


class DeviceRow(QWidget):
    renamed = Signal(str, str)  # device_id, new_name

    MARGIN_H = 6
    SPACING = 8

    def __init__(self, device_id: str, name: str, type_name: DeviceTypeName):
        super().__init__()
        self.device_id = device_id
        self._name = name

        self.name = EditableLabel(name)
        self.name.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )  # long names clip
        style.mark(self.name.label, "row-name", selected=False)
        self.name.text_changed.connect(self._on_text_changed)

        self.badge = Badge()
        self.badge.for_device_type(type_name)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(self.MARGIN_H, 0, self.MARGIN_H, 0)
        lay.setSpacing(self.SPACING)
        lay.addWidget(self.name, 1)
        lay.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.name.label.ensurePolished()
        self.badge.ensurePolished()

    def set_name(self, name: str) -> None:
        self._name = name
        self.name.setText(name)

    def set_selected(self, selected: bool) -> None:
        style.mark(self.name, "row-name", selected=selected)

    def start_editing(self) -> None:
        self.name.start_editing()

    def _on_text_changed(self, text: str) -> None:
        text = text.strip()
        if not text:  # refuse empty names, restore the old one
            self.name.setText(self._name)
            return
        self._name = text
        self.renamed.emit(self.device_id, text)


class DevicesPanel(BasePanel):
    """Panel for managing device list and additions."""

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()
        self.device_types = device_types
        self.device_listbox: DeviceListWidget | None = None
        self.device_type_combo: QComboBox | None = None

        device_events.created.connect(self._device_created)
        device_events.renamed.connect(self._device_renamed)
        device_events.deleted.connect(self.refresh_list)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the devices panel UI elements."""
        title_label = QLabel("Devices")
        style.mark(title_label, "heading")
        layout.addWidget(title_label)

        self.device_listbox = DeviceListWidget(self._delete_selected_device)
        self.device_listbox.setItemDelegate(FullRectDelegate(self.device_listbox))
        self.refresh_list()
        self.device_listbox.itemSelectionChanged.connect(self._on_device_select)
        self.device_listbox.itemSelectionChanged.connect(self._sync_row_selection)

        self.device_listbox.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_listbox.customContextMenuRequested.connect(
            self._show_selected_context_menu
        )
        self.device_listbox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
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

    def refresh_list(self, *args):
        """Refresh the device listbox with current devices."""
        if self.device_listbox is None:
            return
        self.device_listbox.blockSignals(True)
        try:
            self.device_listbox.clear()
            for id, device_entry in global_config.device_store.all().items():
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, id)

                row = DeviceRow(id, device_entry.config.name, device_entry.type_name)
                row.renamed.connect(self._on_row_renamed)
                hint = row.sizeHint()
                item.setSizeHint(QSize(hint.width(), max(hint.height(), 20) + 6))

                self.device_listbox.addItem(item)
                self.device_listbox.setItemWidget(item, row)

        finally:
            self.device_listbox.blockSignals(False)

    def _row(self, item: QListWidgetItem | None) -> DeviceRow | None:
        if item is None or self.device_listbox is None:
            return None
        w = self.device_listbox.itemWidget(item)
        return w if isinstance(w, DeviceRow) else None

    def _sync_row_selection(self):
        if self.device_listbox is None:
            return
        for i in range(self.device_listbox.count()):
            item = self.device_listbox.item(i)
            if row := self._row(item):
                row.set_selected(item.isSelected())

    def _on_row_renamed(self, device_id: str, new_name: str):
        if device_id in global_config.device_store.all():
            ui_signals.devices_req.rename.emit(device_id, new_name)

    def _device_created(self, id: str):
        self.refresh_list()
        row = self._row(self._select_device_by_id(id))
        if row is not None:
            QTimer.singleShot(0, row.start_editing)

    def _on_device_select(self):
        """Handle device selection from listbox."""
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if current_item:
            ui_signals.selection.device.emit(
                current_item.data(Qt.ItemDataRole.UserRole)
            )

    def _device_renamed(self, device_id: str, new_name: str):
        assert self.device_listbox is not None
        for i in range(self.device_listbox.count()):
            item = self.device_listbox.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == device_id:
                self.device_listbox.blockSignals(True)
                try:
                    item.setText(new_name)
                finally:
                    self.device_listbox.blockSignals(False)
                    if row := self._row(item):
                        row.set_name(new_name)
                        row.update()
                        self.device_listbox.viewport().update()
                break

    def _add_device_callback(self):
        """Handle adding a new device."""
        if not self.device_type_combo:
            return
        device_type_name = self.device_type_combo.currentText()
        device_type: DeviceTypeName = next(
            (t for t in list(DeviceTypeName) if t.value == device_type_name),
            DeviceTypeName.MOVING_HEAD,
        )
        ui_signals.devices_req.create.emit(device_type, "")

    def _delete_selected_device(self):
        """Delete the currently selected device."""
        if not self.device_listbox:
            return
        current_item = self.device_listbox.currentItem()
        if not current_item:
            return
        device_id = current_item.data(Qt.ItemDataRole.UserRole)
        if device_id in global_config.device_store.all():
            ui_signals.devices_req.delete.emit(device_id)

    def _duplicate_device(self, device_id: str):
        """Duplicate an existing device with a new unique ID."""
        if device_id not in global_config.device_store.all():
            return
        ui_signals.devices_req.duplicate.emit(device_id)

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
        menu.addAction(duplicate_action)

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
            new_device_action = QAction(device.value, parent=self.device_listbox)
            new_device_action.triggered.connect(
                partial(ui_signals.devices_req.create.emit, device, "")
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
