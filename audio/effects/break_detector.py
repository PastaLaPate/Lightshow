from .spike_detector import SpikeDetector, DetectionType

class BreakDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 2, 2, [0, 3], DetectionType.UPPER)

    def detect(self, data):
        return super().detect(data)