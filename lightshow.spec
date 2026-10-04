import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

BASE_DIR = Path(".")
ASSETS_DIR = BASE_DIR / "lightshow" / "gui" / "assets"

ICON_FILE = str(
    ASSETS_DIR / ("lightshow_icon.ico" if IS_WINDOWS else "lightshow_icon.png")
)

datas = [
    (str(ASSETS_DIR), "lightshow/gui/assets"),
    *collect_data_files("soundcard"),
]

a = Analysis(
    ["lightshow/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtOpenGL",
        "PyQt6.QtOpenGLWidgets",
        "pyqtgraph",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt6.QtNetwork",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtSql",
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
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
    strip=False,
    upx=IS_WINDOWS,
    upx_exclude=[],
    name="lightshow-windows" if IS_WINDOWS else "lightshow-linux",
)
