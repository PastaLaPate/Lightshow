from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel


class Badge(QLabel):
    def __init__(
        self, text: str | None = None, color: QColor | None = None, parent=None
    ):
        super().__init__(parent)
        self._color = color or QColor(255, 0, 0)
        self.setText(text or "")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(18, 18)
        self.update_style()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, color: QColor):
        self._color = color
        self.update_style()

    def update_style(self):
        hex_color = self._color.name(QColor.NameFormat.HexRgb)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {hex_color};
                color: white;
                border-radius: 9px;
                font-weight: bold;
                font-size: 12px;
                padding-left: 6px;
                padding-right: 6px;
            }}
        """)
