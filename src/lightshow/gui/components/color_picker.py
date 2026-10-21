from PySide6.QtCore import QMargins, Qt, Signal
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget


class ColorPicker(QWidget):
    color_changed = Signal(str)

    def __init__(self, color: QColor | None = None):
        super().__init__()
        self._color = color if color and color.isValid() else QColor("#000000")

        layout = QHBoxLayout()
        layout.setContentsMargins(QMargins(0, 0, 0, 0))

        self.dialog = QColorDialog()

        self._preview_btn = QPushButton()
        self._preview_btn.clicked.connect(self.open_dialog)
        self._preview_btn.setFixedSize(24, 24)
        self._preview_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._textedit = QLineEdit(self._color.name(QColor.NameFormat.HexRgb))
        self._textedit.editingFinished.connect(self.editingFinished)
        self._textedit.textChanged.connect(self._update_realtime_preview)

        layout.addWidget(self._preview_btn)
        layout.addWidget(self._textedit)
        self.setLayout(layout)

        self._update_preview_style()

    def color(self) -> QColor:
        return self._color

    def setColor(self, color: QColor):
        self._color = color
        self._textedit.setText(color.name(QColor.NameFormat.HexRgb))
        self._update_preview_style()

    def open_dialog(self):
        color = self.dialog.getColor(self.color())
        if color.isValid():
            self.setColor(color)
            self.color_changed.emit(color.name(QColor.NameFormat.HexRgb))

    def _update_realtime_preview(self, text: str):
        color = QColor(text)
        if color.isValid():
            self._update_preview_style(color)

    def _update_preview_style(self, color: QColor | None = None):
        hex_str = (color or self._color).name(QColor.NameFormat.HexRgb)
        self._preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_str};
                border: 1px solid #555555;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 1px solid #888888;
            }}
        """)

    def editingFinished(self):
        color = QColor(self._textedit.text())
        if color.isValid():
            self.setColor(color)
            self.color_changed.emit(color.name(QColor.NameFormat.HexRgb))
        else:
            self._textedit.setText(self._color.name(QColor.NameFormat.HexRgb))
