from .spike_detector import SpikeDetector, DetectionType

class KickDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 3, 20, [0, 3], DetectionType.UPPER, 0/10000, 250/1000)

    def detect(self, data):
        result = super().detect(data)
        return result