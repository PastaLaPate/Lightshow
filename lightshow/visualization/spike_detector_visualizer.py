from collections import deque

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

from lightshow.audio import detectors


class SpikeDetectorVisualizer(QWidget):
    """PyQt6-based visualizer for spike detector data."""

    def __init__(
        self,
        spike_detector: detectors.SpikeDetector,
        visualization_len=1000,
        expected_max=2 * 1e13,
    ):
        super().__init__()
        self.spike_detector = spike_detector
        self.visualization_len = visualization_len
        self.energy_history = deque(maxlen=visualization_len)
        self.limit_history = deque(maxlen=visualization_len)
        self.diff_history = deque(maxlen=visualization_len)
        self.global_index = 0
        self.expected_max = expected_max

        self.marker_data = {
            "beat": {"indices": [], "energies": []},
            "break": {"indices": [], "energies": []},
            "drop": {"indices": [], "energies": []},
        }

        # UI setup
        self.setMinimumHeight(300)
        self.setStyleSheet("background-color: #1e1e1e;")

    def __call__(
        self, data, beat_detected=False, break_detected=False, drop_detected=False
    ):
        """Process audio data and update visualization."""
        current_energy = data.get_ps_mean(self.spike_detector.freq_range)
        self.energy_history.append(current_energy)

        if len(self.energy_history) > 3:
            self.diff_history.append(
                self.energy_history[-1] - self.energy_history[-4]
                if self.energy_history[-1] > self.energy_history[-4]
                else 0
            )
        else:
            self.diff_history.append(0)

        if len(self.spike_detector.energy_history) < 1:
            self.global_index += 1
            return

        avg_energy = sum(self.spike_detector.energy_history) / len(
            self.spike_detector.energy_history
        )
        limit = self.spike_detector.sensitivity * avg_energy
        self.limit_history.append(limit)

        # Add markers
        self._add_marker("beat", beat_detected, current_energy)
        self._add_marker("break", break_detected, current_energy)
        self._add_marker("drop", drop_detected, current_energy)

        self.global_index += 1

    def _add_marker(self, marker_type, detected, current_energy):
        """Add a marker if detected."""
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

    def qt_update(self):
        """Trigger Qt repaint."""
        self.update()

    def paintEvent(self, event):
        """Paint the visualization with a framed plot area and legend box."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        if not self.energy_history:
            return

        # Layout/margins for plot area
        left_margin = 40
        top_margin = 20
        right_margin = 10
        bottom_margin = 30

        plot_x = left_margin
        plot_y = top_margin
        plot_w = max(10, width - left_margin - right_margin)
        plot_h = max(10, height - top_margin - bottom_margin)

        # Draw plot background (slightly lighter than widget background)
        plot_bg = QColor(43, 43, 43)
        painter.fillRect(plot_x, plot_y, plot_w, plot_h, plot_bg)

        # Draw plot border
        border_pen = QPen(QColor(120, 120, 120), 1)
        painter.setPen(border_pen)
        painter.drawRect(plot_x, plot_y, plot_w, plot_h)

        # Calculate scaling within plot area
        max_energy = max(
            max(self.energy_history) if self.energy_history else 0,
            max(self.limit_history) if self.limit_history else 0,
            self.expected_max,
        )
        if max_energy == 0:
            max_energy = 1

        denom = max(1, len(self.energy_history) - 1)
        scale_x = plot_w / denom
        scale_y = plot_h / max_energy

        # Helper to map data index/value to pixel coords
        def data_x(i):
            return int(plot_x + (i * scale_x))

        def data_y(value):
            return int(plot_y + plot_h - (value * scale_y))

        # Draw energy line (cyan)
        painter.setPen(QPen(QColor(0, 255, 255), 2))
        for i in range(1, len(self.energy_history)):
            x1 = data_x(i - 1)
            y1 = data_y(self.energy_history[i - 1])
            x2 = data_x(i)
            y2 = data_y(self.energy_history[i])
            painter.drawLine(x1, y1, x2, y2)

        # Draw diff line (yellow)
        painter.setPen(QPen(QColor(255, 255, 0), 1))
        for i in range(1, len(self.diff_history)):
            x1 = data_x(i - 1)
            y1 = data_y(self.diff_history[i - 1])
            x2 = data_x(i)
            y2 = data_y(self.diff_history[i])
            painter.drawLine(x1, y1, x2, y2)

        # Draw limit line (red dashed)
        painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        for i in range(1, len(self.limit_history)):
            x1 = data_x(i - 1)
            y1 = data_y(self.limit_history[i - 1])
            x2 = data_x(i)
            y2 = data_y(self.limit_history[i])
            painter.drawLine(x1, y1, x2, y2)

        # Draw marker vertical lines and small filled circles
        marker_colors = {
            "beat": QColor(0, 255, 0),  # Green
            "break": QColor(255, 165, 0),  # Orange
            "drop": QColor(255, 0, 255),  # Magenta
        }
        marker_radius = 4
        # vertical marker lines (subtle)
        for marker_type, data in self.marker_data.items():
            color = marker_colors[marker_type]
            line_pen = QPen(color, 1)
            line_pen.setColor(color)
            line_pen.setWidth(1)
            # make lines slightly transparent
            # QColor supports alpha in constructor, but we keep pen color and set alpha via QColor
            for idx in data["indices"]:
                relative_idx = idx - (self.global_index - len(self.energy_history))
                if 0 <= relative_idx < len(self.energy_history):
                    x = data_x(relative_idx)
                    painter.setPen(
                        QPen(QColor(color.red(), color.green(), color.blue(), 100), 1)
                    )
                    painter.drawLine(x, plot_y, x, plot_y + plot_h)
        for marker_type, data in self.marker_data.items():
            color = marker_colors[marker_type]
            painter.setPen(QPen(color, 1))
            painter.setBrush(color)
            for idx, energy in zip(data["indices"], data["energies"]):
                relative_idx = idx - (self.global_index - len(self.energy_history))
                if 0 <= relative_idx < len(self.energy_history):
                    x = data_x(relative_idx)
                    y = data_y(energy)
                    painter.drawEllipse(
                        x - marker_radius,
                        y - marker_radius,
                        marker_radius * 2,
                        marker_radius * 2,
                    )

        # Draw legend box (top-right inside plot)
        painter.setFont(QFont("Arial", 9))
        entries = [
            ("Energy", QColor(0, 255, 255)),
            ("Diff", QColor(255, 255, 0)),
            ("Limit", QColor(255, 0, 0)),
            ("Beat", marker_colors["beat"]),
            ("Break", marker_colors["break"]),
            ("Drop", marker_colors["drop"]),
        ]
        entry_h = 18
        padding = 6
        box_w = 150
        box_h = padding * 2 + len(entries) * entry_h
        box_x = plot_x + plot_w - box_w - 8
        box_y = plot_y + 8

        # semi-transparent background
        painter.fillRect(box_x, box_y, box_w, box_h, QColor(20, 20, 20, 180))
        painter.setPen(QPen(QColor(140, 140, 140), 1))
        painter.drawRect(box_x, box_y, box_w, box_h)

        # Draw each legend entry
        text_x = box_x + 28
        y = box_y + padding
        for label, color in entries:
            # draw color swatch
            swatch_x = box_x + 8
            swatch_y = y + (entry_h // 2) - 6
            painter.fillRect(swatch_x, swatch_y, 12, 12, color)
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawText(text_x, y + 12, label)
            y += entry_h

    def clear(self):
        """Clear all visualization data."""
        self.energy_history.clear()
        self.limit_history.clear()
        self.diff_history.clear()
        for marker_type in self.marker_data:
            self.marker_data[marker_type]["indices"].clear()
            self.marker_data[marker_type]["energies"].clear()
