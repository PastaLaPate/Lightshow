import subprocess
from typing import Tuple

import semver

from lightshow.utils.config import VERSION

REPO = "https://github.com/PastaLaPate/Lightshow.git"


def fetch_last_tag(strip_v=True) -> str:
    output_lines = subprocess.check_output(
        [
            "git",
            "ls-remote",
            "--tags",
            "--refs",
            "--sort=version:refname",
            REPO,
        ],
        encoding="utf-8",
    ).splitlines()
    last_line_ref = output_lines[-1].rpartition("/")[-1]
    return last_line_ref if not strip_v else last_line_ref.lstrip("v")


def is_update_available() -> Tuple[bool, str]:
    latest_version = fetch_last_tag()
    r = semver.compare(VERSION, latest_version)
    if r == -1:
        return (True, f"New version available: {latest_version}")
    elif r == 0:
        return (False, "You are up to date!")
    elif r == 1:
        return (False, "NIGHTLY BUILD.")
    return (False, "")
