from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["lightshow/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
    (
    "lightshow/gui/assets",
    "./lightshow/gui/assets"),
    *collect_data_files("soundcard"),],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "pyqtgraph",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQT6"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    debug=False,
    runtime_tmpdir=None,
    name="lightshow",
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="lightshow/gui/assets/lightshow_icon.png"
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="lightshow-linux",
)
