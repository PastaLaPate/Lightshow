from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lightshow.devices.device import Device
from lightshow.gui.utils import ui_signals

from .base_panel import BasePanel


class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""

    def __init__(self, device_types: list[type[Device]]):
        super().__init__()
        self.device_types = device_types
        self.selected_device_id = None

        # UI Elements
        self.device_name_input = None
        self.device_type_label = None
        self.props_layout = None
        self.prop_widgets = {}
        self.connect_button = None
        self.delete_button = None
        self.status_label = None
        self.progress_bar = None
        self.details_layout = None
        self.details_widget = None
        self.placeholder_label = None
        # Showed props (runtime/debug info) UI
        self.showed_props_layout = None
        self.showed_prop_labels: dict[str, QLabel] = {}
        self._current_live_device = None

        ui_signals.device_selected.connect(self.device_selected)

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the device details panel UI elements."""
        # Title
        title_label = QLabel("Device Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Placeholder
        self.placeholder_label = QLabel("Select a device to see its details.")
        layout.addWidget(self.placeholder_label)

        # Details group (hidden by default)
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout()

        # Device name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Device Name:"))
        self.device_name_input = QLineEdit()
        self.device_name_input.setReadOnly(True)
        name_layout.addWidget(self.device_name_input)
        self.details_layout.addLayout(name_layout)

        # Device type
        self.device_type_label = QLabel("Type: -")
        self.details_layout.addWidget(self.device_type_label)

        # Runtime / debug properties shown by the live device
        self.showed_props_layout = QVBoxLayout()
        self.details_layout.addLayout(self.showed_props_layout)

        # Editable properties area (populated dynamically)
        self.props_layout = QVBoxLayout()
        self.details_layout.addLayout(self.props_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.details_layout.addWidget(separator)
        self.details_widget.setLayout(self.details_layout)

        # Control buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        # self.connect_button.clicked.connect(self._connect_device_callback)
        button_layout.addWidget(self.connect_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Makes it animate
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)

        self.delete_button = QPushButton("Delete")
        # self.delete_button.clicked.connect(self._delete_device)
        button_layout.addWidget(self.delete_button)

        self.details_layout.addLayout(button_layout)

        # Status
        self.status_label = QLabel("Status: Disconnected")
        self.details_layout.addWidget(self.status_label)

        self.details_layout.addStretch()
        layout.addWidget(self.details_widget)

    def device_selected(self, device_id: str | None):
        print(device_id)
        if device_id:
            pass
        else:
            if self.details_widget:
                self.details_widget.hide()
