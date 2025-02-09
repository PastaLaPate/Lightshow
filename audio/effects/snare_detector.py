from .spike_detector import SpikeDetector, DetectionType

class SnareDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 7.5, 100, [20, 20_000], DetectionType.UPPER)

    def detect(self, data):
        result = super().detect(data)
        return result