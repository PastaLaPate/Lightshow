import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

SPEC_DIR = Path(SPECPATH)
ROOT = SPEC_DIR.parent  # repo root
SRC = ROOT / "src"  # drop this if you don't use a src/ layout
ASSETS_DIR = SRC / "lightshow" / "gui" / "assets"
ICON_FILE = str(
    ASSETS_DIR / ("lightshow_icon.ico" if IS_WINDOWS else "lightshow_icon.png")
)

datas = [
    (str(ASSETS_DIR), "lightshow/gui/assets"),
    *collect_data_files("soundcard"),
]

a = Analysis(
    [str(SPEC_DIR / "entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "pyqtgraph",
        "pyqtgraph.opengl",
        "OpenGL",
        "OpenGL.GL",
        "OpenGL.platform.glx",
        "OpenGL.platform.egl",
        "OpenGL.arrays.numpymodule",
        "OpenGL.arrays.ctypesarrays",
        "OpenGL.arrays.lists",
        "OpenGL.arrays.numbers",
        "OpenGL.arrays.strings",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Safe to exclude as aint imported
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtSql",
        # Not imported too
        "matplotlib",
        "kiwisolver",
        "tkinter",
    ],
    noarchive=False,
    optimize=2,
)

UNWANTED_BINARIES = ("qt6qml", "qt6quick", "qt6pdf", "qpdf")


def _keep_binary(entry):
    name = Path(entry[0]).name.lower()
    return not any(p in name for p in UNWANTED_BINARIES)


def _keep_data(entry):
    parts = Path(entry[0]).parts
    return not ("PySide6" in parts and "translations" in parts)


a.binaries = [b for b in a.binaries if _keep_binary(b)]
a.datas = [d for d in a.datas if _keep_data(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    debug=False,
    bootloader_ignore_signals=False,
    strip=IS_LINUX,
    upx=IS_WINDOWS,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
    name="lightshow",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=IS_LINUX,
    upx=IS_WINDOWS,
    upx_exclude=[],
    name="lightshow-windows" if IS_WINDOWS else "lightshow-linux",
)
