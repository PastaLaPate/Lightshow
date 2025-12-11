from pathlib import Path
from typing import Any, Dict
from NodeGraphQt import NodeGraph, NodesTreeWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightshow.gui.node_editor.nodes.sources import BooleanNodeDataModel

from .custom_node import CustomNode
from .datas import BooleanData, IntegerData

"""
def hook_graph_signals(graph):
    Attach evaluation hooks to the graph.
    
    @graph.port_connected.connect
    def on_port_connected(out_port, in_port):
        node = in_port.node()
        if isinstance(node, CustomNode):
            node.mark_dirty()

    @graph.port_disconnected.connect
    def on_port_disconnected(out_port, in_port):
        node = in_port.node()
        if isinstance(node, CustomNode):
            node.mark_dirty()

    @graph.property_changed.connect
    def on_property_changed(node, prop_name, value):
        if isinstance(node, CustomNode):
            node.mark_dirty()

    @graph.port_connected.connect
    def on_port_connected(out_port, in_port):
        node = in_port.node()
        if isinstance(node, DisplayNode):
            node.evaluate()


"""

BASE_PATH = Path(__file__).parent.resolve()

class NotGate(CustomNode):
    __identifier__ = "io.github.pastalapate"

    NODE_NAME = "Not Gate"

    def __init__(self):

        super(NotGate, self).__init__()

        # create an input port.

        self.add_typed_input(BooleanData, name="bool_in")
        self.add_typed_output(BooleanData, name="bool_out")

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"bool_out": not inputs["bool_in"]}

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
        self.graph.register_node(BooleanNodeDataModel)
        hotkey_path = Path(BASE_PATH, 'hotkeys', 'hotkeys.json')
        self.graph.set_context_menu_from_file(hotkey_path, 'graph')

        layout = QVBoxLayout()
        layout.addWidget(self.graph.widget)
        self.setLayout(layout)

        self.setWindowTitle("Node Editor")
        self.resize(800, 600)
