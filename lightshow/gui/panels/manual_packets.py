from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QVBoxLayout, QGridLayout, QPushButton, QSizePolicy

from lightshow.devices.device import PacketData, PacketStatus, PacketType

from .base_panel import BasePanel


class Button(QPushButton):

    def __init__(self, label: str):
        super().__init__(label)
        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )

    def sizeHint(self) -> QSize:
        default_size = super().sizeHint()
        default_size.setHeight(default_size.height() + 30)
        return default_size


class ManualPacketsSenderPanel(BasePanel):
    def __init__(self):
        super().__init__()
        self.buttons = [
            ("Send Beat", PacketData(PacketType.BEAT, PacketStatus.ON)),
            ("Send Break On", PacketData(PacketType.BREAK, PacketStatus.ON)),
            ("Send Break Off", PacketData(PacketType.BREAK, PacketStatus.OFF)),
            ("Send Tick", PacketData(PacketType.TICK, PacketStatus.ON)),
            ("Send new Music ON", PacketData(PacketType.NEW_MUSIC, PacketStatus.ON)),
            ("Send new Music OFF", PacketData(PacketType.NEW_MUSIC, PacketStatus.OFF)),
        ]

    def create_qt_ui(self, layout: QVBoxLayout):
        grid = QGridLayout()
        for i, (label, packet) in enumerate(self.buttons):
            button = Button(label)
            button.clicked.connect(
                lambda _, p=packet: self.trigger("send_manual_packet", p)
            )
            grid.addWidget(button, i // 3, i % 3)
        layout.addLayout(grid)
