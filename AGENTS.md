# Lightshow Development Guide

## Overview

Python GUI app for controlling DIY moving head projectors via audio beat detection. Uses PyQt6/PySide6 for UI and pyqtgraph for visualizations.

## Setup

```bash
# Install dependencies (use uv as recommended)
uv sync

# Linux dev dependencies (needed for building)
sudo apt install libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsdl1.2-dev libsmpeg-dev librtmidi-dev
# or
sudo dnf install rtmidi-devel

# Run development
uv run lightshow
```

## Building

```bash
# Full dev install with extras
uv sync --dev

# Build wheel
uv build

# Build executable (uses PyInstaller)
uv run pyinstaller packaging/lightshow.spec
# or
make build

# Windows: requires NSIS (choco install nsis)
uv run pyinstaller packaging/installer/lightshow.nsi
```

## Development Commands

- `make dev` - Run app
- `make build` - Build with PyInstaller
- `make install` - Install with `uv sync --locked --all-extras`
- `make commit` - Conventional commit with commitizen
- `make hooks` - Install pre-commit hooks

## Linting & Type Checking

```bash
uvx ruff check --fix
uvx ty check
```

## Code Style

- **Reactive properties**: Use `@property` decorator for variables that should react to changes. Store internal value in `self._variable_name`.
- **Qt conventions**: UI component setters/getters should follow Qt naming (e.g., `getText()`, `setText(value: str)`, `text()`).
- **Type hints**: Annotate types as narrowly as possible.

## Architecture

- **Entry point**: `src/lightshow/__main__.py` → `src/lightshow/app.py`
- **Core modules**: `audio/` (beat detection), `devices/` (projector control), `gui/` (UI)
- **Platform tracking**: DBUS (Linux) / WinRT (Windows) via `lightshow.media`
- **Audio stream**: `lightshow.audio.streams.LoopbackAudioStreamHandler` captures speaker output

## Platform-Specific Code

- **Windows**: Uses `winrt-runtime` packages, `LOCALAPPDATA` for config, Windows-specific app user model ID
- **Linux**: Uses `dbus-next`, `XDG_DATA_HOME` for config, strips binaries with PyInstaller

## Packaging

- **Spec file**: `packaging/lightshow.spec` defines PyInstaller configuration
- **Exclusions**: matplotlib, kiwisolver, tkinter (safe to exclude)
- **Assets**: `src/lightshow/gui/assets/` (icon, etc.)
- **Hidden imports**: OpenGL modules, PySide6 submodules (see spec file)

## Testing

No test files currently present. When adding tests:

- Audio detectors in `src/lightshow/audio/detectors/` may need mock audio streams
- Device controllers may need mock device instances

## Scripts

- `scripts/debug_audio.py` - List available audio devices/mics
- `scripts/cz_conventional_chore.py` - Custom commitizen plugin

## Version & Release

- Uses commitizen: `uv run cz bump` / `uv run cz version`
- Tags follow `v$version` format (PEP440)
- Version stored in `pyproject.toml`

Use context7 for following libraries: pyqtgraph, Qt for Python for pyside6 and Pydantic
