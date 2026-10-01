from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QStackedLayout,
    QVBoxLayout,
)

from lightshow.devices.device import Device
from lightshow.gui.utils import ui_signals

from .base_panel import BasePanel


class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()
        self.device_types: list[type[Device]] = device_types
        self.stacked_layout: QStackedLayout | None = None

        ui_signals.device_selected.connect(self.device_selected)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the device details panel UI elements."""
        # Title
        title_label = QLabel("Device Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Placeholder
        self.placeholder_label = QLabel("Select a device to see its details.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.stacked_layout = QStackedLayout()
        self.stacked_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stacked_layout.addWidget(self.placeholder_label)

        layout.addWidget(title_label)
        layout.addLayout(self.stacked_layout)

    def device_selected(self, device_id: str | None):
        assert self.stacked_layout is not None
        print(device_id)
        if device_id:
            self.stacked_layout.setCurrentIndex(0)
        else:
            self.stacked_layout.setCurrentIndex(1)
