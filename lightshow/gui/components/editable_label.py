import PyQt6.QtCore
from PyQt6 import QtGui
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class EditableLabel(QWidget):
    text_changed = pyqtSignal(str)

    def __init__(self, text="", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(text, self)
        self.line_edit = QLineEdit(text, self)
        self.line_edit.hide()

        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)

        self.line_edit.returnPressed.connect(self._to_label)
        self.line_edit.installEventFilter(self)
        self.setLayout(layout)

    def text(self):
        return self.label.text()

    def setText(self, text: str):
        self.label.setText(text)
        self.line_edit.setText(text)

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent | None):
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self._to_line_edit()

    def eventFilter(self, a0: PyQt6.QtCore.QObject | None, a1: QEvent | None) -> bool:
        if a1 is not None and a0 == self.line_edit:
            if a1.type() == QEvent.Type.FocusOut:
                self._to_label()
            elif (
                a1.type() == QEvent.Type.KeyPress
                and isinstance(a1, QKeyEvent)
                and a1.key() == Qt.Key.Key_Escape
            ):
                self.line_edit.setText(self.label.text())
                self._to_label()
                return True
        return False

    def _to_label(self):
        if self.label.text() != self.line_edit.text():
            self.text_changed.emit(self.line_edit.text())
        self.label.setText(self.line_edit.text())
        self.line_edit.hide()
        self.label.show()

    def _to_line_edit(self):
        self.label.hide()
        self.line_edit.show()
        self.line_edit.setFocus()
        self.line_edit.selectAll()
