# Lightshow
A software designed to control the [DIY Moving Head projector](https://github.com/PastaLaPate/DIY_MovingHeadLight)
> [!CAUTION]
> Software made for windows
## Installation
### Setup
> [!IMPORTANT]  
> The setup is made for windows
Setup in releases.
### Compile from source
> [!TIP]
> UV Is recommended

1. Clone repo
   `git clone https://github.com/PastaLaPate/Lightshow`
2. Go to dir
   `cd Lightshow`
4. Install dependencies
   `uv sync`
5. Start
   `uv run lightshow`
6. (Optional) Create executable
   `uv run pyinstaller .\lightshow.spec`
## Stack
QT for ui.
pyqtgraph for visualization.
PyAudioWPatch for audio stream, numpy for treatment.
