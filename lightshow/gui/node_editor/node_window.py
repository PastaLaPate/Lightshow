from pathlib import Path
from typing import Any, Dict

from NodeGraphQt import NodeGraph
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightshow.gui.node_editor.custom_viewer import CustomNodeViewer
from lightshow.gui.node_editor.nodes.colors import register_colors
from lightshow.gui.node_editor.nodes.string import register_string_operations

from .custom_node import CustomNode
from .datas import BooleanData
from .nodes.displays import register_displays
from .nodes.math import register_math_nodes
from .nodes.sources import register_sources


def hook_graph_signals(graph):
    """Attach evaluation hooks to the graph."""

    @graph.port_connected.connect
    def on_port_connected(in_port, out_port):
        node = in_port.node()
        if isinstance(node, CustomNode):
            node.mark_dirty()
            node.evaluate()

    @graph.port_disconnected.connect
    def on_port_disconnected(in_port, out_port):
        node = in_port.node()
        if isinstance(node, CustomNode):
            node.mark_dirty()
            node.evaluate()

    @graph.property_changed.connect
    def on_property_changed(node, prop_name, value):
        if isinstance(node, CustomNode):
            node.mark_dirty()
            node.evaluate()


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


class NodeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.viewer = CustomNodeViewer(parent=self, undo_stack=QUndoStack())
        self.graph = NodeGraph(viewer=self.viewer)
        register_sources(self.graph)
        register_displays(self.graph)
        register_math_nodes(self.graph)
        register_string_operations(self.graph)
        register_colors(self.graph)
        self.graph.register_node(NotGate)
        self.viewer.node_factory = self.graph._node_factory
        hotkey_path = Path(BASE_PATH, "hotkeys", "hotkeys.json")
        self.graph.set_context_menu_from_file(hotkey_path, "graph")
        hook_graph_signals(self.graph)
        layout = QVBoxLayout()
        layout.addWidget(self.graph.widget)  # type: ignore
        self.setLayout(layout)
        self.setStyleSheet('QWidget {font: "Roboto Mono"}')

        self.setWindowTitle("Node Editor")
        self.resize(800, 600)
