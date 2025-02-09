from .spike_detector import SpikeDetector, DetectionType

class BreakDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 3, 10, [0, 3], DetectionType.LOWER)

    def detect(self, data):
        result = super().detect(data)
        return result