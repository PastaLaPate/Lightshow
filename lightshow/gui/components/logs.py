from PyQt6.QtWidgets import QTextEdit, QFrame, QVBoxLayout, QPushButton

from lightshow.gui.panels.base_panel import BasePanel
from lightshow.utils.logger import LoggerCore


class Logs(BasePanel):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.textBox = None
        self.clearButton = None

    def create_qt_ui(self, layout: QVBoxLayout):
        frameLayout = QVBoxLayout()
        frameLayout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.frame.setLayout(frameLayout)

        self.textBox = QTextEdit()
        self.textBox.setReadOnly(True)
        self.textBox.setStyleSheet("""                  
            QTextEdit {
                background: #111;
                color: #eee;
                font-family: Consolas;
                font-size: 12px;
            }
        """)
        LoggerCore().attach_widget(self.textBox)
        frameLayout.addWidget(self.textBox)
        
        self.clearButton = QPushButton("Clear")
        self.clearButton.clicked.connect(lambda: self.textBox.clear())
        
        layout.addWidget(self.frame)
        layout.addWidget(self.clearButton)
