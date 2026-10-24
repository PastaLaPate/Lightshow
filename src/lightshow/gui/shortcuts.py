from enum import StrEnum

from PySide6.QtGui import QAction, QKeySequence


class Shortcuts(StrEnum):
    UNDO = "edit.undo"
    REDO = "edit.redo"
    RENAME = "edit.rename"


class ShortcutMap:
    # TODO: Make it editable + conflict detection
    def __init__(self):
        self.map: dict[Shortcuts, list[QKeySequence]] = {
            Shortcuts.UNDO: [QKeySequence(QKeySequence.StandardKey.Undo)],
            Shortcuts.REDO: [
                QKeySequence(QKeySequence.StandardKey.Redo),
                QKeySequence("Ctrl+Y"),
            ],
            Shortcuts.RENAME: [QKeySequence("F2")],
        }

    def __getitem__(self, key: Shortcuts) -> list[QKeySequence]:
        return self.map[key]

    def apply(self, action: QAction, key: Shortcuts):
        action.setShortcuts(self[key])
