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
Wheel file is available, download in releases, run `pip install lightshow-X.XX.X.py3-none-any.whl`.

### Windows

#### Installer

Installer needing admin in the releases.

#### Portable

Portable also available in the releases.
Download, extract.
Run lightshow.exe

### Linux

#### AppImage
Download the AppImage.
Make it executable: `chmod +x downloaded_file.AppImage`

#### Portable
Download the .tar.gz archive.
Make the `lightshow` file executable: `cd extracted_folder && chmod +x lightshow`

### MacOS
Im not even sure it works.

### Run from source

> [!TIP]
> UV is recommended

1. Clone repo
   `git clone https://github.com/PastaLaPate/Lightshow`
2. Go to dir
   `cd Lightshow`
3. Install dependencies
   `uv sync`
4. Start
   `uv run lightshow`
5. (Optional) Create executable for windows
   `uv run pyinstaller .\lightshow.spec`

## Contributions

Feel free to open prs to fix code or add new devices.

## Stack

QT for ui.

PyQTGraph for visualization.

Soundcard for audio stream, numpy for treatment.
