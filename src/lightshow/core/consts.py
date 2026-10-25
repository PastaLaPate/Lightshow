import os
import sys


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore
        relative_path = relative_path.removeprefix("src/")
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
