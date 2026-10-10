import os

from lightshow.media.abstract_tracker import ATrackTracker

PlatformSpecificTracker: type[ATrackTracker]
if os.name == "nt":
    from lightshow.tracks_tracker.windows import WindowsTracksInfoTracker

    PlatformSpecificTracker = WindowsTracksInfoTracker
elif os.name == "posix":
    from lightshow.media.linux import LinuxTracksInfoTracker

    PlatformSpecificTracker = LinuxTracksInfoTracker
else:
    # Unknown platform, define a dummy tracker that does nothing
    class PlatformSpecificTracker(ATrackTracker):
        def start(self) -> None:
            pass
