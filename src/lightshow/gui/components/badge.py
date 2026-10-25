from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QSizePolicy

from lightshow.devices.registry import DEVICE_CLASSES
from lightshow.devices.types import DeviceTypeName
from lightshow.gui.theme import style


class Badge(QLabel):
    def __init__(
        self, text: str | None = None, color: QColor | None = None, parent=None
    ):
        super().__init__(parent)
        self._color = color or QColor(255, 0, 0)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        style.mark(self, "badge")
        self.setText(text or "")
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
        self.updateGeometry()

    def for_device_type(self, type_name: DeviceTypeName):
        self.setText(type_name)
        self.color = QColor(DEVICE_CLASSES[type_name].BADGE_COLOR)
