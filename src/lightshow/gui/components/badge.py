from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel

from lightshow.gui.theme import style


class Badge(QLabel):
    def __init__(
        self, text: str | None = None, color: QColor | None = None, parent=None
    ):
        super().__init__(parent)
        self._color = color or QColor(255, 0, 0)
        self.setText(text or "")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(18, 18)
        style.mark(self, "badge")
        self._apply_color()

    def setText(self, text: str):
        super().setText(text)
        self._apply_color()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, color: QColor):
        self._color = color
        self._apply_color()

    def _apply_color(self):
        is_dot = not self.text()
        if is_dot:
            self.setFixedSize(18, 18)
        else:
            self.setMinimumSize(18, 18)
            self.setMaximumSize(16777215, 16777215)

        parts = []
        if self._color is not None:
            lum = (
                0.299 * self._color.red()
                + 0.587 * self._color.green()
                + 0.114 * self._color.blue()
            )
            parts.append(f"background-color: {self._color.name()};")
            parts.append(f"color: {'#000' if lum > 160 else '#fff'};")
        if is_dot:
            parts.append("padding: 0;")
        self.setStyleSheet(" ".join(parts))
