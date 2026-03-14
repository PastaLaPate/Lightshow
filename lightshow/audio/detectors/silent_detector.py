from lightshow.audio.audio_types import AudioData


class SilentDetector:
    def detect(self, data: AudioData):
        # Use mel energies for silence detection - more accurate across frequency spectrum
        return data.get_mel_mean([0, 40]) < 2 * 1e5  # Mean of all mel bins
