# Lightshow

![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/PastaLaPate/Lightshow)
![GitHub Repo stars](https://img.shields.io/github/stars/PastaLaPate/Lightshow)
![GitHub Tag](https://img.shields.io/github/v/tag/PastaLaPate/Lightshow?sort=semver&label=version)

A software designed to control the [DIY Moving Head projector](https://github.com/PastaLaPate/DIY_MovingHeadLight)

> [!CAUTION]
> Software made for windows and linux. Needs port audio to work!

## Installation

### Setup

> [!IMPORTANT]  
> The setup is made for windows
> Setup in releases.

### Run from source

> [!TIP]
> UV Is recommended

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

Sounddevice for audio stream, numpy for treatment.
