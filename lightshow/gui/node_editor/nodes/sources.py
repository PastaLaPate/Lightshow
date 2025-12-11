from typing import Any, Dict

from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import BooleanData, DecimalData, IntegerData


def register_sources(graph: NodeGraph):
    graph.register_nodes([BooleanSourceNode, IntegerSourceNode, FloatSourceNode])


class BooleanSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Boolean Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_checkbox("in_cb", "", "Out", False)
        self.add_typed_output(BooleanData, name="bool_out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"bool_out": self.get_property("in_cb")}


class IntegerSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Integer Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_text_input("in_text", "", "0", "Integer val here")
        self.add_typed_output(IntegerData, name="int_out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = self.get_property("in_text")
        value = value if isinstance(value, str) else ""

        return {
            "int_out": IntegerData.parse(value) if IntegerData.validate(value) else 0
        }


class FloatSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Float Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_text_input("in_text", "", "0.0", "Float val here")
        self.add_typed_output(DecimalData, name="float_out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = self.get_property("in_text")
        value = value if isinstance(value, str) else ""

        return {
            "float_out": (
                DecimalData.parse(value) if DecimalData.validate(value) else 0.0
            )
        }
