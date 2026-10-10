from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QSlider,
    QSpinBox,
    QWidget,
)


class NumericSliderSpinBox(QWidget):
    valueChanged = Signal(object)

    def __init__(self, min_: float = 0, max_: float = 0, step: float = 1, parent=None):
        super().__init__(parent)

        self.slider: QSlider | None = None
        self.spinbox: QDoubleSpinBox | QSpinBox | None = None

        self.min = min_
        self.max = max_
        self.step = step

        self.is_float = (
            isinstance(step, float)
            or isinstance(min_, float)
            or isinstance(max_, float)
        )

        self.decimals: int = 0
        self.multiplier: int = 1
        if self.is_float:
            _sign, _digits, exponent = Decimal(self.step).as_tuple()
            if isinstance(exponent, int):
                self.decimals = -exponent
                self.multiplier = 10**self.decimals

    def _construct_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.slider = QSlider(Qt.Orientation.Horizontal)

        if self.is_float:
            self.slider.setRange(
                int(self.min * self.multiplier), int(self.max * self.multiplier)
            )
            self.slider.setSingleStep(int(self.step * self.multiplier))
        else:
            self.slider.setRange(int(self.min), int(self.max))
            self.slider.setSingleStep(int(self.step))

        if self.is_float:
            self.spinbox = QDoubleSpinBox()
            self.spinbox.setDecimals(self.decimals)
            self.spinbox.setRange(self.min, self.max)
            self.spinbox.setSingleStep(self.step)
        else:
            self.spinbox = QSpinBox()
            self.spinbox.setRange(int(self.min), int(self.max))
            self.spinbox.setSingleStep(int(self.step))

        layout.addWidget(self.spinbox)
        layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self._on_slider_changed)

    def _on_slider_changed(self, value: int):
        final_value: float | int = value / self.multiplier if self.is_float else value

        if self.spinbox:
            self.spinbox.blockSignals(True)
            if isinstance(self.spinbox, QDoubleSpinBox):
                self.spinbox.setValue(final_value)
            else:
                self.spinbox.setValue(int(final_value))
            self.spinbox.blockSignals(False)

        self.valueChanged.emit(final_value)

    def _on_spinbox_float_changed(self, value: float):
        assert self.slider is not None
        self.slider.blockSignals(True)
        self.slider.setValue(int(value * self.multiplier))
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)

    def _on_spinbox_int_changed(self, value: int):
        assert self.slider is not None
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)

    def value(self):
        assert self.spinbox is not None
        return self.spinbox.value()

    def setValue(self, value):
        assert self.spinbox is not None
        self.spinbox.setValue(value)
