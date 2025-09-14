from lightshow.audio.audio_types import AudioData


class SilentDetector:
    def detect(self, data: AudioData):
        return data.get_ps_mean([0, 20000]) < 2 * 1e5  # 1e6 bcs it's a silent detector
