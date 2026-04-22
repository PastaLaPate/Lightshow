# Bootstrap for app.py
# Setups logger before importing other modules to ensure all logs are captured
import os
import signal
import sys
import traceback
from pathlib import Path

from lightshow.utils import Logger
from lightshow.utils.logger import configure_logging

logger = None


def terminate(sig: int, frame: object) -> None:
    # Type ignore as signal is registered after the logger is initialized, so it will always be set when this function is called
    logger.info("Interrupt signal caught! Stopping gracefully...")  # type: ignore
    from .app import terminate

    try:
        terminate()
    except Exception:
        logger.error(  # type: ignore
            f"Damn, that's some very bad luck: double termination error bruh. \n {traceback.format_exc()}"
        )
    sys.exit(0)


if __name__ == "__main__":
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    configure_logging("Lightshow", base / ".LightShow")
    logger = Logger.for_class("Bootstrapper")
    signal.signal(signal.SIGINT, terminate)
    from .app import main

    main()
