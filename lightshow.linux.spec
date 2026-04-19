a = Analysis(
    ["lightshow/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[("lightshow/gui/assets", "./lightshow/gui/assets")],
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
    excludes=[],
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
    name="lightshow-linux",
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