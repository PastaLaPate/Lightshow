from PySide6.QtWidgets import QVBoxLayout, QWidget


class BasePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create Qt UI elements. Override in subclasses."""
