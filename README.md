# Lightshow

![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/PastaLaPate/Lightshow)
![GitHub Repo stars](https://img.shields.io/github/stars/PastaLaPate/Lightshow)
![GitHub Tag](https://img.shields.io/github/v/tag/PastaLaPate/Lightshow?sort=semver&label=version)

A software designed to control the [DIY Moving Head projector](https://github.com/PastaLaPate/DIY_MovingHeadLight)

> [!CAUTION]
> Software made for windows and linux.

It detects beats from the output stream of your speakers and then use them to create beautiful lightshows.

## Installation

### Multi-platform

Wheel file is available, download in releases, run

```bash
pip install lightshow-X.XX.X.py3-none-any.whl
```

### Windows

#### Installer

Installer needing admin in the releases.

#### Portable

Portable also available in the releases.
Download, extract.
Run `lightshow.exe`

### Linux

#### AppImage

Download the AppImage.
Make it executable:

```bash
chmod +x lightshow-X.XX.X-x86_64.AppImage
```

#### Portable

Download the .tar.gz archive.
Make the `lightshow` file executable & execute:

```bash
cd extracted_folder
chmod +x lightshow
./lightshow
```

### MacOS

Im not even sure it works.

### Run from source

> [!TIP]
> UV is recommended

1. Clone repo
   ```bash
   git clone https://github.com/PastaLaPate/Lightshow
   ```
2. Go to dir
   ```bash
   cd Lightshow
   ```
3. Install dependencies
   ```bash
   uv sync
   ```
4. Linux dev dependencies
   1. Using apt: <br>
      ```bash
      sudo apt install libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsdl1.2-dev libsmpeg-dev librtmidi-dev
      ```
   2. Using dnf: <br>
      ```bash
      sudo dnf install rtmidi-devel
      ```

5. Start
   ```bash
   uv run lightshow
   ```

## Building

Make sure you have dev dependencies:

```bash
uv sync --dev
```

### Wheel

```bash
uv build
```

Wheel is in `dist/`

### Windows

Install NSIS.
With chocolatery: `choco install nsis`

Build using pyinstaller: `uv run pyinstaller lightshow.spec`

### Linux

Build using pyinstaller: `uv run pyinstaller lightshow.linux.spec`

## Contributions

Feel free to open prs to fix code or add new devices.

## Stack

PyQT6 for ui.
PyQt6-Charts.
PyQTGraph for visualization.
DBUS/winrt for tracks tracking.

Soundcard for audio stream, numpy for treatment.

```

```
