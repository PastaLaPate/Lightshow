from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lightshow.gui.panels.base_panel import BasePanel
from lightshow.utils.config import Setting, SettingListItem, SettingTab


class SettingsDialog(QDialog, BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 450)

        self._pending_changes: dict[str, int | float | str | bool | list] = {}
        self._setting_widgets: dict[str, QWidget] = {}
        self._list_items: list[SettingListItem] = []

        self.search_bar = QLineEdit()
        self.settings_list = QListWidget()
        self.settings_stack = QStackedWidget()

        self.setup_ui()

    def setup_ui(self):
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

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def load(self, items: list[SettingListItem]) -> None:
        """Populate the dialog from a list of SettingListItems."""
        self._list_items = items
        self.settings_list.clear()
        while self.settings_stack.count():
            self.settings_stack.removeWidget(self.settings_stack.widget(0))
        self._setting_widgets.clear()
        self._pending_changes.clear()

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

    # ------------------------------------------------------------------ #
    # Page / widget builders                                               #
    # ------------------------------------------------------------------ #

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
            tabs.addTab(self._build_tab(tab, item.id), tab.name)
        layout.addWidget(tabs, stretch=1)
        return page

    def _build_tab(self, tab: SettingTab, section_id: str) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        for setting in tab.settings:
            control = self._build_control(setting)
            form.addRow(setting.name, control)

        return widget

    def _build_control(self, setting: Setting) -> QWidget:
        from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox

        widget: QWidget

        if setting.type is bool:
            widget = QCheckBox()
            widget.setChecked(setting.default is True)
            widget.checkStateChanged.connect(
                lambda state, sid=setting.id: self._record(
                    sid, state == Qt.CheckState.Checked
                )
            )

        elif setting.type is int:
            widget = QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            if isinstance(setting.default, int):
                widget.setValue(setting.default)
            widget.valueChanged.connect(lambda v, sid=setting.id: self._record(sid, v))

        elif setting.type is float:
            widget = QDoubleSpinBox()
            widget.setRange(-2147483648, 2147483647)
            if isinstance(setting.default, (int, float)):
                widget.setValue(float(setting.default))
            widget.valueChanged.connect(lambda v, sid=setting.id: self._record(sid, v))

        elif setting.type is list and setting.options:
            widget = QComboBox()
            widget.addItems([str(o) for o in setting.options])
            if setting.default in setting.options:
                widget.setCurrentIndex(setting.options.index(setting.default))
            widget.currentIndexChanged.connect(
                lambda i, sid=setting.id, opts=setting.options: self._record(
                    sid, opts[i]
                )
            )

        else:
            widget = QLineEdit()
            widget.setText(str(setting.default) if setting.default is not None else "")
            widget.textChanged.connect(lambda v, sid=setting.id: self._record(sid, v))

        widget.setToolTip(setting.description)
        self._setting_widgets[setting.id] = widget
        return widget

    # ------------------------------------------------------------------ #
    # Slots                                                                #
    # ------------------------------------------------------------------ #

    def _record(self, setting_id: str, value: int | float | str | bool | list) -> None:
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
                    self._restore_widget(setting)
        self._pending_changes.clear()

    def _restore_widget(self, setting: Setting) -> None:
        from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox

        widget = self._setting_widgets.get(setting.id)
        if widget is None or setting.default is None:
            return

        if isinstance(widget, QCheckBox):
            widget.setChecked(setting.default is True)
        elif isinstance(widget, QSpinBox) and isinstance(setting.default, int):
            widget.setValue(setting.default)
        elif isinstance(widget, QDoubleSpinBox) and isinstance(
            setting.default, (int, float)
        ):
            widget.setValue(float(setting.default))
        elif (
            isinstance(widget, QComboBox)
            and setting.options
            and setting.default in setting.options
        ):
            widget.setCurrentIndex(setting.options.index(setting.default))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(setting.default))

    def _on_search(self, text: str) -> None:
        query = text.strip().lower()
        for i in range(self.settings_list.count()):
            item = self.settings_list.item(i)
            assert item is not None
            item.setHidden(bool(query and query not in item.text().lower()))
