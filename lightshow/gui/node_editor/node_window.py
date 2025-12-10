from NodeGraphQt import NodeGraph, NodesTreeWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .custom_node import CustomNode
from .datas import BooleanData, IntegerData


class BoolTest(CustomNode):

    # unique node identifier domain.

    __identifier__ = "io.github.pastalapate"

    # initial default node name.

    NODE_NAME = "Boolean Test"

    def __init__(self):

        super(BoolTest, self).__init__()

        # create an input port.

        self.add_typed_input(BooleanData, name="bool_in")

        # create an output port.

        self.add_typed_output(BooleanData, name="bool_out")


class IntTest(CustomNode):
    __identifier__ = "io.github.pastalapate"
    NODE_NAME = "Integer Test"

    def __init__(self):
        super(IntTest, self).__init__()
        self.add_typed_input(IntegerData, name="int_in")
        self.add_typed_output(IntegerData, name="int_out")


class NodeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.graph = NodeGraph()
        self.graph.register_node(BoolTest)
        self.graph.register_node(IntTest)
        self.tree_widget = NodesTreeWidget(parent=None, node_graph=self.graph)
        self.tree_widget.show()

        layout = QVBoxLayout()
        layout.addWidget(self.graph.widget)
        self.setLayout(layout)

        self.setWindowTitle("Node Editor")
        self.resize(800, 600)
