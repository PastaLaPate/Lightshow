from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qtpynodeeditor import DataModelRegistry, FlowScene, FlowView

from .nodes.Test import NaiveDataModel


class NodeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.registry = DataModelRegistry()
        self.registry.register_model(NaiveDataModel, "Test")

        self.scene = FlowScene(registry=self.registry)
        self.view = FlowView(self.scene)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.setWindowTitle("Node Editor")
        self.resize(800, 600)
