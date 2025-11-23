# Tested only on window

## Binaries in releases

## Compile from source

UV Is recommended

1. Clone repo
   `git clone https://github.com/PastaLaPate/Lightshow`
2. Create venv
   `python -m venv venv`
3. Activate venv
   `.\venv\Scripts\activate`
4. Install dependencies
   `uv sync`
5. Run
   `uv run lightshow`
6. (Optional) Create executable
   `uv run pyinstaller .\__main__.spec`
