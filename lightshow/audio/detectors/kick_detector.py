from lightshow.audio.data import AudioData
from lightshow.audio.detectors.methods.detection_method import DetectionMethod
from lightshow.utils.logger import Logger

from .spike_detector import DetectionType, SpikeDetector

logger = Logger.for_class("KickDetector")


class KickDetector(SpikeDetector):
    def __init__(self, AudioHandler, detection_method: type[DetectionMethod]):
        super().__init__(
            AudioHandler,
            0,
            0,
            [0, 1],  # kept here for SpikeDetector compat
            DetectionType.UPPER,
            1 / 10000,
            250 / 1000,
        )
        self.was_above = False
        self.detector = detection_method()

    def reset_state(self):
        """Reset detector state without clearing energy history."""
        self.detector.cooldown_counter = 0
        self.detector.was_above = False

    def clear(self):
        self.detector.clean()

    def detect(self, data: AudioData, append_current_energy=True):
        return self.detector.detect(data, append_current_energy)
