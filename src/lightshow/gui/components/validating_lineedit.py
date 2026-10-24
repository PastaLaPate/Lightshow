from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit

from lightshow.core.fields import ValidationScheme
from lightshow.gui.utils.field_validator import validate_value


class ValidatingLineEdit(QLineEdit):
    committed = Signal(str)

    _ERROR_STYLE = "QLineEdit { border: 1px solid #d93025; border-radius: 3px; }"

    def __init__(
        self, text: str = "", validation_scheme: ValidationScheme = ValidationScheme.Any
    ):
        super().__init__(text)
        self._validation_scheme = validation_scheme
        self._committed_text = text
        self.editingFinished.connect(self._on_editing_finished)
        self.textChanged.connect(self._on_text_changed)
        self._on_text_changed(text)

    @property
    def committed_text(self) -> str:
        return self._committed_text

    def setText(self, text: str | None) -> None:
        self._committed_text = text or ""
        super().setText(text)

    def _on_text_changed(self, text: str):
        valid = validate_value(self._validation_scheme, text)
        if valid:
            self.setStyleSheet("")
            self.setToolTip("")
        else:
            self.setStyleSheet(self._ERROR_STYLE)
            self.setToolTip(f"Invalid text of type {self._validation_scheme}")

    def _on_editing_finished(self) -> None:
        old, new = self._committed_text, self.text()
        if new == old:
            return
        if validate_value(self._validation_scheme, new):
            self._committed_text = new
            self.committed.emit(new)
        else:
            self.setText(old)
