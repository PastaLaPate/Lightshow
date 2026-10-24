from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from lightshow.gui.theme import Theme, style


class CollapsibleSection(QWidget):
    toggled = Signal(bool)

    def __init__(self, title: str, level: int = 0, expanded: bool = True, parent=None):
        super().__init__(parent)

        self._level = level

        self.header = QToolButton()
        style.mark(self.header, "section-header", level=level)
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.header.setProperty("level", level)
        self.header.toggled.connect(self._on_toggled)

        self.content = QFrame()
        style.mark(self.content, "section-content")

        body = QVBoxLayout(self.content)
        body.setContentsMargins(12 if level else 8, 6, 6, 6)
        body.setSpacing(4)

        self.form = QFormLayout()  # section's fields
        self.form.setContentsMargins(0, 2, 0, 4)
        self.form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self._apply_metrics(style.theme)
        body.addLayout(self.form)

        self.children_layout = QVBoxLayout()
        self.children_layout.setContentsMargins(0, 0, 0, 0)
        body.addLayout(self.children_layout)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addWidget(self.content)

        self._on_toggled(expanded)

    def _on_toggled(self, expanded: bool):
        self.header.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.content.setVisible(expanded)
        self.toggled.emit(expanded)

    def _apply_metrics(self, t: Theme):
        self.form.setHorizontalSpacing(t.form_h_spacing)
        self.form.setVerticalSpacing(t.form_v_spacing)
