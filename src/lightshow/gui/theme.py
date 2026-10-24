from dataclasses import dataclass, replace
from string import Template

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget


@dataclass(frozen=True)
class Theme:
    name: str
    # surfaces
    window: str  # app / dialog background
    panel: str  # inspector / form background
    header: str  # category header (level 1+)
    header_top: str  # category header (level 0)
    header_hover: str
    input_bg: str
    input_border: str
    # text
    text: str
    text_dim: str
    text_disabled: str
    # accent
    accent: str
    accent_text: str = "#ffffff"
    # metrics
    radius: int = 6
    radius_small: int = 3
    padding: int = 8


UE_DARK = Theme(
    name="ue-dark",
    window="#242424",
    panel="#1a1a1a",
    header="#2b2b2b",
    header_top="#303030",
    header_hover="#363636",
    input_bg="#0f0f0f",
    input_border="#3a3a3a",
    text="#d0d0d0",
    text_dim="#9a9a9a",
    text_disabled="#5c5c5c",
    accent="#0070e0",
)

LIGHT = Theme(
    name="light",
    window="#f0f0f0",
    panel="#ffffff",
    header="#e4e4e4",
    header_top="#d8d8d8",
    header_hover="#cfcfcf",
    input_bg="#ffffff",
    input_border="#b8b8b8",
    text="#202020",
    text_dim="#606060",
    text_disabled="#a0a0a0",
    accent="#0070e0",
)

# Big ass QSS
_QSS = Template("""
QMainWindow, QDialog { background: $window; }

/* tabs */
QTabWidget::pane {
    background: $panel; border: 1px solid $header; border-radius: ${radius_small}px;
}
QTabBar::tab {
    background: $header; color: $text_dim;
    padding: 5px 12px; border: none;
    border-top-left-radius: ${radius_small}px; border-top-right-radius: ${radius_small}px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: $panel; color: $text; }
QTabBar::tab:hover:!selected { background: $header_hover; }


/* lists / trees */
QListView, QTreeView, QTableView {
    background: $panel; color: $text; border: 1px solid $header;
    border-radius: ${radius_small}px; outline: none;
}
QListView::item, QTreeView::item { padding: 3px 6px; }
QListView::item:hover, QTreeView::item:hover { background: $header; }
QListView::item:selected, QTreeView::item:selected {
    background: $accent; color: $accent_text;
}

/* UE-style spinboxes: no buttons */
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    width: 0; border: none;
}


/* checkboxes */
QCheckBox::indicator {
    width: 14px; height: 14px;
    background: $input_bg; border: 1px solid $input_border;
    border-radius: ${radius_small}px;
}
QCheckBox::indicator:hover   { border-color: $accent; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }

/* separators */
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: $header; }

/* menus */
QMenuBar { background: $window; color: $text; }
QMenuBar::item:selected, QMenu::item:selected { background: $accent; color: $accent_text; }
QMenu { background: $header; color: $text; border: 1px solid $input_border; padding: 4px; }
QMenu::item { padding: 4px 18px; border-radius: ${radius_small}px; }


/* semantic roles */
QLabel[role="heading"] { font-size: 14px; font-weight: 600; color: $text; }
QLabel[role="badge"] {
    background: $header_top; color: $text; border-radius: 9px; padding: 1px 8px;
    font-weight: 600;
}
QTextEdit[role="console"], QPlainTextEdit[role="console"] {
    background: $panel;
    color: $text;
    border: 1px solid $header;
    font-family: "JetBrains Mono", monospace;
    font-size: 13px;
}

/* ---------- panels ---------- */
QWidget[role="panel"] {
    background: $panel;
    border-radius: ${radius}px;
}
QWidget[role="section-content"] {
    background: transparent;
    border: none;
}

/* ---------- collapsible headers ---------- */
QToolButton[role="section-header"] {
    border: none;
    border-radius: ${radius_small}px;
    padding: 4px 6px;
    text-align: left;
    font-weight: 600;
    color: $text;
    background: $header;
}
QToolButton[role="section-header"][level="0"] { background: $header_top; }
QToolButton[role="section-header"]:hover      { background: $header_hover; }

/* ---------- inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: $input_bg;
    color: $text;
    border: 1px solid $input_border;
    border-radius: ${radius_small}px;
    padding: 2px 4px;
    selection-background-color: $accent;
    selection-color: $accent_text;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border-color: $accent;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: $text_disabled;
    border-color: $header;
}
QLineEdit:read-only { color: $text_dim; }

/* ---------- buttons ---------- */
QPushButton {
    background: $header_top;
    color: $text;
    border: 1px solid $input_border;
    border-radius: ${radius_small}px;
    padding: 4px 12px;
}
QPushButton:hover    { background: $header_hover; }
QPushButton:pressed  { background: $accent; color: $accent_text; }
QPushButton:disabled { color: $text_disabled; }
QPushButton[role="primary"] { background: $accent; color: $accent_text; border-color: $accent; }

/* ---------- misc ---------- */
QLabel { background: transparent; }
QLabel[role="dim"] { color: $text_dim; }
QScrollArea { border: none; background: transparent; }
QToolTip {
    background: $header_top; color: $text;
    border: 1px solid $input_border; padding: 3px;
}

/* ---------- scrollbars ---------- */
QScrollBar:vertical   { background: transparent; width: 10px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: $header_hover; border-radius: 4px; min-height: 24px; min-width: 24px;
}
QScrollBar::handle:hover { background: $input_border; }
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page { background: none; border: none; width: 0; height: 0; }
""")


class StyleManager(QObject):
    def __init__(self):
        super().__init__()
        self._theme: Theme = UE_DARK
        self._app: QApplication | None = None
        self._themes: dict[str, Theme] = {}
        for t in (UE_DARK, LIGHT):
            self.register(t)

    # registry

    def register(self, theme: Theme):
        self._themes[theme.name] = theme

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def available(self) -> list[str]:
        return list(self._themes)

    # api

    def install(self, app: QApplication, theme: Theme | str | None = None):
        self._app = app
        app.setStyle("Fusion")  # consistent base that respects the palette
        self.set_theme(theme or self._theme)

    def set_theme(self, theme: Theme | str):
        if isinstance(theme, str):
            theme = self._themes[theme]
        self._theme = theme
        if self._app is None:
            return
        self._app.setPalette(self._build_palette(theme))
        self._app.setStyleSheet(_QSS.substitute(vars(theme)))

    def tweak(self, **overrides):
        """Derive and apply a modified copy of the current theme."""
        self.set_theme(replace(self._theme, **overrides))

    # helpers
    def mark(self, widget: QWidget, role: str, **props) -> QWidget:
        """Tag a widget with a style role (and extra props) and re-polish it."""
        widget.setProperty("role", role)
        for k, v in props.items():
            widget.setProperty(k, v)
        if role == "panel":
            # plain QWidget ignores QSS background/border without this
            widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        return widget

    @staticmethod
    def _build_palette(t: Theme) -> QPalette:
        p = QPalette()
        C, G = QPalette.ColorRole, QPalette.ColorGroup
        roles = {
            C.Window: t.window,
            C.WindowText: t.text,
            C.Base: t.input_bg,
            C.AlternateBase: t.panel,
            C.Text: t.text,
            C.PlaceholderText: t.text_dim,
            C.Button: t.header_top,
            C.ButtonText: t.text,
            C.ToolTipBase: t.header_top,
            C.ToolTipText: t.text,
            C.Highlight: t.accent,
            C.HighlightedText: t.accent_text,
            C.Link: t.accent,
            C.BrightText: "#ffffff",
        }
        for role, color in roles.items():
            p.setColor(role, QColor(color))
        for role in (C.WindowText, C.Text, C.ButtonText):
            p.setColor(G.Disabled, role, QColor(t.text_disabled))
        return p


style = StyleManager()
