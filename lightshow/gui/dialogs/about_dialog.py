from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from lightshow.utils.config import ARCH, OS, PYTHON_VERSION, VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Lightshow")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        title_label = QLabel("<h1>Lightshow</h1>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        description_label = QLabel(
            "<h3> Lightshow is a real-time music visualization tool that detects beats and breaks in audio and creates stunning light effects. "
            "It uses advanced audio processing techniques to analyze the music and generate dynamic visualizations that sync perfectly with the rhythm. </h3>"
        )
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        disclaimer_label = QLabel(
            "<i>Note: This is an early version of Lightshow. Expect some rough edges and missing features as we continue to develop and improve the software.</i>"
        )
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        debug_label = QLabel(
            f"<code> OS : {OS}, Python {PYTHON_VERSION}, Architecture: {ARCH}, QT {QT_VERSION_STR}, PyQt {PYQT_VERSION_STR}, Lightshow {VERSION}</code>"
        )
        debug_label.setWordWrap(True)

        credit_label = QLabel("<i> Coded with ❤️ by PastaLaPate</i>")
        credit_label.setWordWrap(True)

        layout.addWidget(disclaimer_label)
        layout.addWidget(description_label)
        layout.addWidget(debug_label)
        layout.addWidget(credit_label)

        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        self.setLayout(layout)
