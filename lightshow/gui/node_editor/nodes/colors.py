from typing import Any, Dict

from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import Color, ColorData, IntegerData


def register_colors(graph: NodeGraph):
    graph.register_nodes([ColorFromInts])


class ColorFromInts(CustomNode):
    NODE_NAME = "Color from Ints"
    __identifier__ = "io.github.pastalapate.colors"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(IntegerData, "R", multi_input=False)
        self.add_typed_input(IntegerData, "G", multi_input=False)
        self.add_typed_input(IntegerData, "B", multi_input=False)
        self.add_typed_output(ColorData, "Color3", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"Color3": Color(r=inputs["R"], g=inputs["G"], b=inputs["B"])}


class ColorFromHex(CustomNode):
    NODE_NAME = "Color from hex"
    __identifier__ = "io.github.pastalapate.colors"
