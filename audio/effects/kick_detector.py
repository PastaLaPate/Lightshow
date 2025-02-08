from .spike_detector import SpikeDetector, DetectionType

class KickDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 2.5, 10, [0, 3], DetectionType.UPPER)

    def detect(self, data):
        result = super().detect(data)
        return result