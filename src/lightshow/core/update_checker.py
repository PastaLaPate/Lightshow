import requests
import semver

from lightshow.core.config import VERSION

REPO = "https://github.com/PastaLaPate/Lightshow.git"


def fetch_last_tag():
    url = "https://api.github.com/repos/PastaLaPate/Lightshow/releases/latest"

    # Optional: Add a user-agent to comply with GitHub API guidelines
    headers = {"Accept": "application/vnd.github+json"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data.get("tag_name")[1:]  # remove v prefix
    else:
        return f"Error: {response.status_code} - {response.text}"


def is_update_available() -> tuple[bool, str]:
    latest_version = fetch_last_tag()
    print(latest_version)
    r = semver.compare(VERSION, latest_version)
    if r == -1:
        return (True, f"New version available: {latest_version}")
    elif r == 0:
        return (False, "You are up to date!")
    elif r == 1:
        return (False, "NIGHTLY BUILD.")
    return (False, "")
