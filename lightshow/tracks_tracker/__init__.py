import os
from typing import Type

from lightshow.tracks_tracker.abstract_tracker import ATrackTracker

PlatformSpecificTracker: Type[ATrackTracker]
if os.name == "nt":
    from lightshow.tracks_tracker.windows import WindowsTracksInfoTracker

    PlatformSpecificTracker = WindowsTracksInfoTracker
elif os.name == "posix":
    from lightshow.tracks_tracker.linux import LinuxTracksInfoTracker

    PlatformSpecificTracker = LinuxTracksInfoTracker
else:
    # Unknown platform, define a dummy tracker that does nothing
    class PlatformSpecificTracker(ATrackTracker):
        def start(self) -> None:
            pass
