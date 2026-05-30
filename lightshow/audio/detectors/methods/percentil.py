import numpy as np

from lightshow.audio.data import AudioData
from lightshow.audio.detectors.methods.detection_method import DetectionMethod


class Percentile(DetectionMethod):
    def __init__(self):
        super().__init__(
            sensitivity=1.75,
            sample_rate=44100,
            chunk_size=1024,
            window_size=20.0,
            bin_range=[0, 2],
            cooldown_time=0.25,
        )
        self.percentile = 15
        self.transient_threshold = 0.3

        self.smoothed_baseline = None
        self.baseline_attack = 0.995
        self.baseline_decay = 0.999

        self.append_energy = False

    @classmethod
    def name(cls):
        return "Percentile"

    def detect(self, audio_data: AudioData, append_current_energy=True) -> bool:
        current_energy = self.register_energy(audio_data, append_current_energy)

        sub_energy = audio_data.get_ps_mean([0, 2])
        transient_energy = audio_data.get_ps_mean([2, 5])
        transient_ratio = transient_energy / (sub_energy + 1e-9)

        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            self.was_above = False
            return False

        if len(self.energy_history) < 7:
            self.was_above = False
            return False

        current_diff = 0
        if len(self.energy_history) > 4:
            prev = self.energy_history[-4]
            current_diff = max(0.0, current_energy - prev)

        self._update_baseline = append_current_energy
        limit = self.get_limit()

        is_above = current_diff > limit and transient_ratio > self.transient_threshold
        detected = is_above and not self.was_above
        if detected:
            self.cooldown_counter = self.cooldown_frame_duration

        is_settled = current_energy < (self.smoothed_baseline or 0 * 0.8)

        if is_above and not self.was_above:
            detected = True
            self.cooldown_counter = self.cooldown_frame_duration
            self.was_above = True
        elif not is_above and is_settled:
            self.was_above = False
        return detected

    def get_limit(self) -> float:
        if len(self.energy_history) < 7:
            return 0
        raw_baseline = np.percentile(self.energy_history, self.percentile)

        if self.smoothed_baseline is None:
            self.smoothed_baseline = raw_baseline
            return self.sensitivity * self.smoothed_baseline

        if getattr(self, "_update_baseline", True):
            alpha = (
                self.baseline_attack
                if raw_baseline > self.smoothed_baseline
                else self.baseline_decay
            )
            self.smoothed_baseline = (
                alpha * self.smoothed_baseline + (1 - alpha) * raw_baseline
            )

        return self.sensitivity * self.smoothed_baseline
