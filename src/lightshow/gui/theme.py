import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from string import Template

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from lightshow.core.consts import resource_path

_ARROW_POINTS = {"up": "1,6 5,1 9,6", "down": "1,1 5,6 9,1"}


def _arrow_svg(direction: str, color: str) -> Path:
    d = Path(tempfile.gettempdir()) / "lightshow_theme"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{direction}_{color.lstrip('#')}.svg"
    if not p.exists():
        p.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="7" viewBox="0 0 10 7">'
            f'<polygon points="{_ARROW_POINTS[direction]}" fill="{color}"/></svg>'
        )
    return p


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
    # form metrics
    form_h_spacing: int = 12  # gap between label and field
    form_v_spacing: int = 6  # gap between rows
    input_pad_v: int = 4
    input_pad_h: int = 6
    row_min_height: int = 24


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

theme_template_file = resource_path("src/lightshow/gui/assets/theme.qss")
with open(theme_template_file, mode="r") as f:
    theme_text = f.read()

_QSS = Template(theme_text)


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
        self._app.setStyleSheet(
            _QSS.substitute({**vars(theme), **self._arrow_urls(theme)})
        )

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

    def _arrow_urls(self, t: Theme) -> dict[str, str]:
        return {
            "arrow_up": _arrow_svg("up", t.text_dim).as_posix(),
            "arrow_up_hover": _arrow_svg("up", t.text).as_posix(),
            "arrow_down": _arrow_svg("down", t.text_dim).as_posix(),
            "arrow_down_hover": _arrow_svg("down", t.text).as_posix(),
        }

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
