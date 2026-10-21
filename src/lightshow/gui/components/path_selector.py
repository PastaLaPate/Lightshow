import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from lightshow.devices.fields import FileFilters


class PathSelector(QWidget):
    """A widget for selecting files or directories using QFileDialog."""

    path_changed = Signal(str)

    def __init__(
        self,
        path: str = "",
        title: str | None = None,
        file_mode: QFileDialog.FileMode = QFileDialog.FileMode.AnyFile,
        options: QFileDialog.Option | None = None,
        accept_all_label: str = "Select...",
        filters: list[FileFilters | str] | None = None,
    ):
        super().__init__()

        self.dialog_names: dict[QFileDialog.FileMode, str] = {
            QFileDialog.FileMode.AnyFile: "Select a file",
            QFileDialog.FileMode.ExistingFile: "Select a file",
            QFileDialog.FileMode.ExistingFiles: "Select a or multiple files",
            QFileDialog.FileMode.Directory: "Select a directory",
        }

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select a file or directory...")
        self._path_edit.returnPressed.connect(self.open_dialog)

        self._browse_btn = QPushButton()
        self._browse_btn.clicked.connect(self.open_dialog)
        self._browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout.addWidget(self._path_edit)
        layout.addWidget(self._browse_btn)
        self.setLayout(layout)

        self._path = path
        self._title = title
        self._file_mode = file_mode
        self._options = options
        self._accept_all_label = accept_all_label
        self._filters = filters or [
            "Text Files (*.txt *.log)",
            "Python Files (*.py *.pyw)",
            "JSON Files (*.json)",
            "All Files (*)",
        ]

        if path:
            self._path_edit.setText(path)

    def path(self) -> str:
        """Get the current path."""
        return self._path

    def setPath(self, path: str):
        """Set the current path."""
        self._path = path
        self._path_edit.setText(path)

    def open_dialog(self):
        """Open a file/directory dialog."""
        dialog = QFileDialog(
            self,
            self._title
            if self._title is not None
            else self.dialog_names[self._file_mode],
        )
        dialog.setFileMode(self._file_mode)
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, self._accept_all_label)

        if self._options is not None:
            dialog.setOptions(self._options)

        if self._file_mode == QFileDialog.FileMode.Directory:
            if self._options is None:
                dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        else:
            dialog.setNameFilters(self._filters)
            dialog.selectNameFilter(self._filters[-1])

        if self._path:
            dialog.setDirectory(os.path.dirname(self._path) or ".")
            dialog.selectFile(self._path)

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return

        selected = dialog.selectedFiles()
        if selected:
            self.setPath(selected[0])
            self.path_changed.emit(selected[0])

    def setTitle(self, title: str):
        """Set the dialog title."""
        self._title = title

    def setFileMode(self, file_mode: QFileDialog.FileMode):
        """Set the file mode."""
        self._file_mode = file_mode

    def setOptions(self, options: QFileDialog.Option):
        """Set dialog options."""
        self._options = options

    def setAcceptAllLabel(self, label: str):
        """Set the OK button label."""
        self._accept_all_label = label

    def setFilters(self, filters: list[str]):
        """Set file filters."""
        self._filters = filters
