from PyQt6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from lightshow.gui.utils import lerp_color


class StatusCircle(QWidget):
    def __init__(self, color=Qt.GlobalColor.green, pulsing=False, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._pulse_color = QColor(Qt.GlobalColor.transparent)
        self._t = 0.0

        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.setKeyValueAt(0.0, 0.0)
        self._anim.setKeyValueAt(0.5, 1.0)
        self._anim.setKeyValueAt(1.0, 0.0)
        self._anim.valueChanged.connect(self._on_anim)

        self.set_pulsing(pulsing)

    def _on_anim(self, v):
        self._t = float(v)
        self.update()

    # TODO: Convert to pyqtProperty

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color: Qt.GlobalColor):
        if self._color != color:
            self._color = QColor(color)
            self.update()

    def set_pulsing(self, on: bool):
        if on:
            if self._anim.state() != QVariantAnimation.State.Running:
                self._anim.start()
        else:
            self._anim.stop()
            self._t = 0.0
            self.update()

    def hideEvent(self, a0):
        if self._anim.state() == QVariantAnimation.State.Running:
            self._anim.pause()
        super().hideEvent(a0)

    def showEvent(self, a0):
        if self._anim.state() == QVariantAnimation.State.Paused:
            self._anim.resume()
        super().showEvent(a0)

    def sizeHint(self):
        return QSize(16, 16)

    def minimumSizeHint(self):
        return QSize(8, 8)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, a0):
        return a0

    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        rect = QRectF(
            (self.width() - size) / 2,
            (self.height() - size) / 2,
            size,
            size,
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(lerp_color(self._color, self._pulse_color, self._t))
        p.drawEllipse(rect)
