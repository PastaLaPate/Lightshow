import os

from lightshow.media.base import AbstractTrackTracker

PlatformSpecificTracker: type[AbstractTrackTracker]
if os.name == "nt":
    from lightshow.tracks_tracker.windows import WindowsTracksInfoTracker

    PlatformSpecificTracker = WindowsTracksInfoTracker
elif os.name == "posix":
    from lightshow.media.linux import LinuxTracksInfoTracker

    PlatformSpecificTracker = LinuxTracksInfoTracker
else:
    # Unknown platform, define a dummy tracker that does nothing
    class PlatformSpecificTracker(AbstractTrackTracker):
        def start(self) -> None:
            pass
