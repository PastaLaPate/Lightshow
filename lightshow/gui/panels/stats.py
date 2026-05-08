from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from lightshow.gui.panels.base_panel import BasePanel


class StatsPanel(BasePanel):
    """Panel for audio stream control and visualization."""

    def __init__(
        self,
    ):
        super().__init__()

    def create_qt_ui(self, layout: QVBoxLayout):
        main_layout = QHBoxLayout()
        self.fps_viewer = QLabel("FPS: Unknown")
        main_layout.addWidget(self.fps_viewer)
        layout.addLayout(main_layout)

    def update_fps(self, fps: float):
        self.fps_viewer.setText(f"FPS : {round(fps * 10) / 10}")
