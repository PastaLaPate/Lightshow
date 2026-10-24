from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lightshow.gui.components.collabsible_section import CollapsibleSection
from lightshow.gui.theme import style


class SectionedView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        style.mark(self, "panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._sections: dict[tuple[str, ...], CollapsibleSection] = {}
        self._expanded: dict[
            tuple[str, ...], bool
        ] = {}  # Save if the device gets re-selected

        self._content: QWidget | None = None
        self._root_layout: QVBoxLayout | None = None

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 8, 8, 8)
        self._outer.addWidget(self._scroll)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        return QSize(240, 160)

    def minimumSizeHint(self) -> QSize:
        return QSize(120, 60)

    def _reset(self) -> None:
        self._sections.clear()

        if self._content is not None:
            self._content.setParent(None)
            self._content.deleteLater()

        self._content = QWidget()
        self._root_layout = QVBoxLayout(self._content)
        self._root_layout.setContentsMargins(0, 0, 4, 0)
        self._root_layout.setSpacing(2)

        self._scroll.setWidget(self._content)
        self._content.setAutoFillBackground(False)

    def _section(self, path: tuple[str, ...]) -> CollapsibleSection:
        if path in self._sections:
            return self._sections[path]

        parent_layout = (
            self._section(path[:-1]).children_layout
            if len(path) > 1
            else self._root_layout
        )  # Recursively find parent
        if parent_layout is None:
            raise RuntimeError("Wasnt initialized.")
        sec = CollapsibleSection(
            path[-1], level=len(path) - 1, expanded=self._expanded.get(path, True)
        )
        sec.toggled.connect(lambda e, p=path: self._expanded.__setitem__(p, e))
        parent_layout.addWidget(sec)
        self._sections[path] = sec
        return sec

    def _add_row(self, category: str, label: str, widget: QWidget) -> None:
        path = tuple(p.strip() for p in category.split("/"))
        self._section(path).form.addRow(label, widget)

    def _finish(self) -> None:
        if self._root_layout is not None:
            self._root_layout.addStretch(1)
        self._align_labels()

    def _align_labels(self) -> None:
        groups = []
        for sec in self._sections.values():
            labels = []
            for r in range(sec.form.rowCount()):
                item = sec.form.itemAt(r, QFormLayout.ItemRole.LabelRole)
                if item and (w := item.widget()) is not None:  # Spicy syntax
                    labels.append(w)
            if labels:
                groups.append((sec._level, labels))
        if not groups:
            return
        target = max(ind + max(l.sizeHint().width() for l in ls) for ind, ls in groups)
        for ind, ls in groups:
            for l in ls:
                l.setMinimumWidth(target - ind)
