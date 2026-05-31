from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lightshow.gui.panels.base_panel import BasePanel
from lightshow.utils.config import Setting, SettingListItem, SettingTab


class SettingsDialog(QDialog, BasePanel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 450)

        self._pending_changes: dict[str, Any] = {}
        self._setting_widgets: dict[str, QWidget] = {}
        self._list_items: list[SettingListItem] = []

        self.search_bar = QLineEdit()
        self.settings_list = QListWidget()
        self.settings_stack = QStackedWidget()

        self._setup_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # Layout
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        self.search_bar.setPlaceholderText("Search settings…")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self._on_search)
        root_layout.addWidget(self.search_bar)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)

        self.settings_list.setFixedWidth(180)
        self.settings_list.currentRowChanged.connect(
            self.settings_stack.setCurrentIndex
        )
        content_layout.addWidget(self.settings_list)
        content_layout.addWidget(self.settings_stack, stretch=1)

        root_layout.addLayout(content_layout, stretch=1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults,
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        assert apply_button is not None
        apply_button.clicked.connect(self._on_apply)

        restore_button = button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        assert restore_button is not None
        restore_button.clicked.connect(self._on_restore)

        root_layout.addWidget(button_box)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def load(
        self,
        items: list[SettingListItem],
        saved_values: dict[str, Any] | None = None,
    ) -> None:
        """
        Populate the dialog from the SETTINGS_CATEGORIES tree, then optionally
        pre-fill every widget with the current saved values.

        Parameters
        ----------
        items:
            Pass ``SETTINGS_CATEGORIES`` from config.py.
        saved_values:
            Flat ``{setting_id: value}`` dict — use
            ``global_config.settings.as_dict()`` to build it.
            When omitted, widgets show their declared defaults.
        """
        self._list_items = items
        self._clear()

        for item in items:
            list_entry = QListWidgetItem(item.name)
            list_entry.setData(Qt.ItemDataRole.UserRole, item.id)
            if item.icon:
                from PyQt6.QtGui import QIcon

                list_entry.setIcon(QIcon(item.icon))
            self.settings_list.addItem(list_entry)
            self.settings_stack.addWidget(self._build_page(item))

        if items:
            self.settings_list.setCurrentRow(0)

        if saved_values:
            self.load_saved(saved_values)

    def load_saved(self, values: dict[str, Any]) -> None:
        """
        Pre-populate every widget from a flat ``{setting_id: value}`` dict
        without marking any change as pending.

        Typically called right after ``load()``::

            dialog.load(SETTINGS_CATEGORIES, saved_values=global_config.settings.as_dict())

        Can also be called standalone to refresh an already-open dialog.
        """
        for item in self._list_items:
            for tab in item.tabs:
                for setting in tab.settings:
                    if setting.id not in values:
                        continue
                    widget = self._setting_widgets.get(setting.id)
                    if widget is None:
                        continue
                    self._set_widget_value(widget, values[setting.id], setting)

    # ──────────────────────────────────────────────────────────────────────────
    # Page / widget builders
    # ──────────────────────────────────────────────────────────────────────────

    def _build_page(self, item: SettingListItem) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel(f"<b>{item.name}</b>")
        layout.addWidget(header)

        if not item.tabs:
            layout.addStretch()
            return page

        tabs = QTabWidget()
        for tab in item.tabs:
            tabs.addTab(self._build_tab(tab), tab.name)
        layout.addWidget(tabs, stretch=1)
        return page

    def _build_tab(self, tab: SettingTab) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for setting in tab.settings:
            control = self._build_control(setting)
            form.addRow(setting.name, control)
        return widget

    def _build_control(self, setting: Setting[Any]) -> QWidget:
        widget: QWidget

        if setting.type is bool:
            cb = QCheckBox()
            cb.setChecked(bool(setting.default))
            cb.checkStateChanged.connect(
                lambda state, sid=setting.id: self._record(
                    sid, state == Qt.CheckState.Checked
                )
            )
            widget = cb

        elif setting.type is int and setting.options:
            combo = QComboBox()
            combo.addItems([str(o) for o in setting.options])
            if setting.default in setting.options:
                combo.setCurrentIndex(setting.options.index(setting.default))
            combo.currentIndexChanged.connect(
                lambda i, sid=setting.id, opts=setting.options: self._record(
                    sid, opts[i]
                )
            )
            widget = combo

        elif setting.type is int:
            spin = QSpinBox()
            spin.setRange(-2_147_483_648, 2_147_483_647)
            spin.setValue(int(setting.default))
            spin.valueChanged.connect(lambda v, sid=setting.id: self._record(sid, v))
            widget = spin

        elif setting.type is float:
            dspin = QDoubleSpinBox()
            dspin.setRange(-2_147_483_648.0, 2_147_483_647.0)
            dspin.setDecimals(3)
            dspin.setValue(float(setting.default))
            dspin.valueChanged.connect(lambda v, sid=setting.id: self._record(sid, v))
            widget = dspin

        elif setting.type is str and setting.options:
            combo = QComboBox()
            combo.addItems([str(o) for o in setting.options])
            if setting.default in setting.options:
                combo.setCurrentIndex(setting.options.index(setting.default))
            combo.currentIndexChanged.connect(
                lambda i, sid=setting.id, opts=setting.options: self._record(
                    sid, opts[i]
                )
            )
            widget = combo

        else:
            line = QLineEdit()
            line.setText(str(setting.default) if setting.default is not None else "")
            line.textChanged.connect(lambda v, sid=setting.id: self._record(sid, v))
            widget = line

        widget.setToolTip(setting.description)
        self._setting_widgets[setting.id] = widget
        return widget

    # ──────────────────────────────────────────────────────────────────────────
    # Widget value helper (shared by load_saved and _restore_widget)
    # ──────────────────────────────────────────────────────────────────────────

    def _set_widget_value(
        self,
        widget: QWidget,
        value: Any,
        setting: Setting[Any],
    ) -> None:
        """
        Write *value* into *widget* without triggering _record().
        Signals are blocked for the duration so no pending change is created.
        """
        widget.blockSignals(True)
        try:
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))

            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))

            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value))

            elif isinstance(widget, QComboBox):
                # Options may be ints or strings — match by string representation
                idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)

            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

        finally:
            widget.blockSignals(False)

    # ──────────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────────

    def _record(self, setting_id: str, value: Any) -> None:
        self._pending_changes[setting_id] = value

    def _on_apply(self) -> None:
        if self._pending_changes:
            self.trigger("apply", dict(self._pending_changes))
            self._pending_changes.clear()

    def _on_accept(self) -> None:
        self._on_apply()
        self.accept()

    def _on_restore(self) -> None:
        for item in self._list_items:
            for tab in item.tabs:
                for setting in tab.settings:
                    widget = self._setting_widgets.get(setting.id)
                    if widget is not None:
                        self._set_widget_value(widget, setting.default, setting)
        self._pending_changes.clear()

    def _on_search(self, text: str) -> None:
        query = text.strip().lower()
        for i in range(self.settings_list.count()):
            item = self.settings_list.item(i)
            assert item is not None
            item.setHidden(bool(query and query not in item.text().lower()))

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _clear(self) -> None:
        self.settings_list.clear()
        while self.settings_stack.count():
            self.settings_stack.removeWidget(self.settings_stack.widget(0))
        self._setting_widgets.clear()
        self._pending_changes.clear()
