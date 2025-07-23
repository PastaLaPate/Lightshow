from .spike_detector import SpikeDetector, DetectionType

class KickDetector(SpikeDetector):
    def __init__(self, chunks_per_second):
        super().__init__(chunks_per_second, 2.5, 20, [0, 3], DetectionType.UPPER, 1/10000, 250/1000)

    def detect(self, data, appendCurrentEnergy=True):
        result = super().detect(data, appendCurrentEnergy=appendCurrentEnergy)
        return result