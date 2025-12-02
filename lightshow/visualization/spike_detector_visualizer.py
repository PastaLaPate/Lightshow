from collections import deque
import dearpygui.dearpygui as dpg

from lightshow.audio import detectors


class SpikeDetectorVisualizer:
    def __init__(
        self,
        SpikeDetector: detectors.SpikeDetector,
        vizualisation_len=1000,
        expectedMax=2 * 1e13,
    ):
        self.SpikeDetector = SpikeDetector
        self.energy_history = deque(maxlen=vizualisation_len)
        self.limit_history = deque(maxlen=vizualisation_len)
        self.diff_history = deque(maxlen=vizualisation_len)
        self.global_index = 0
        self.expected_max = expectedMax
        self.dpg_tags = {}
        self.marker_data = {
            "beat": {"indices": [], "energies": []},
            "break": {"indices": [], "energies": []},
            "drop": {"indices": [], "energies": []},
        }

    def dpg_init(self, parent_axis_tag):
        """Initializes DearPyGui series and stores their tags."""
        self.dpg_tags["energy"] = dpg.add_line_series(
            [], [], label="Energy", parent=parent_axis_tag
        )
        self.dpg_tags["diff"] = dpg.add_line_series(
            [], [], label="Diff (-1, -4)", parent=parent_axis_tag
        )
        self.dpg_tags["limit"] = dpg.add_line_series(
            [], [], label="Limit", parent=parent_axis_tag
        )
        self.dpg_tags["beat"] = dpg.add_scatter_series(
            [], [], label="Beat", parent=parent_axis_tag
        )
        self.dpg_tags["break"] = dpg.add_scatter_series(
            [], [], label="Break", parent=parent_axis_tag
        )
        self.dpg_tags["drop"] = dpg.add_scatter_series(
            [], [], label="Drop", parent=parent_axis_tag
        )

    def dpg_update(self):
        """Updates the DearPyGui series with the latest data."""
        if not self.dpg_tags:
            return

        # Update line series
        x_data = [
            self.global_index - len(self.energy_history) + i
            for i in range(len(self.energy_history))
        ]
        dpg.set_value(self.dpg_tags["energy"], [x_data, list(self.energy_history)])
        dpg.set_value(self.dpg_tags["diff"], [x_data, list(self.diff_history)])
        dpg.set_value(self.dpg_tags["limit"], [x_data, list(self.limit_history)])

        # Update scatter series
        for marker_type, data in self.marker_data.items():
            if data["indices"]:
                dpg.set_value(
                    self.dpg_tags[marker_type], [data["indices"], data["energies"]]
                )

    def __call__(
        self, data, beat_detected=False, break_detected=False, drop_detected=False
    ):
        current_energy = data.get_ps_mean(self.SpikeDetector.freq_range)
        self.energy_history.append(current_energy)
        if len(self.energy_history) > 3:
            self.diff_history.append(
                self.energy_history[-1] - self.energy_history[-4]
                if self.energy_history[-1] > self.energy_history[-4]
                else 0
            )
        else:
            self.diff_history.append(0)

        if len(self.SpikeDetector.energy_history) < 1:
            self.global_index += 1
            return

        avg_energy = sum(self.SpikeDetector.energy_history) / len(
            self.SpikeDetector.energy_history
        )
        limit = self.SpikeDetector.sensitivity * avg_energy
        self.limit_history.append(limit)

        # Add markers
        self._add_marker("beat", beat_detected, current_energy)
        self._add_marker("break", break_detected, current_energy)
        self._add_marker("drop", drop_detected, current_energy)

        self.global_index += 1

    def _add_marker(self, marker_type, detected, current_energy):
        if detected:
            self.marker_data[marker_type]["indices"].append(self.global_index)
            self.marker_data[marker_type]["energies"].append(current_energy)
            # Limit memory growth
            maxlen = 50  # Keep last 50 markers
            if len(self.marker_data[marker_type]["indices"]) > maxlen:
                self.marker_data[marker_type]["indices"] = self.marker_data[
                    marker_type
                ]["indices"][-maxlen:]
                self.marker_data[marker_type]["energies"] = self.marker_data[
                    marker_type
                ]["energies"][-maxlen:]

    def clear(self):
        self.energy_history.clear()
        self.limit_history.clear()
        self.diff_history.clear()
        for marker_type in self.marker_data:
            self.marker_data[marker_type]["indices"].clear()
            self.marker_data[marker_type]["energies"].clear()
        # No need to clear global_index, as it tracks absolute time
