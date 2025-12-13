from typing import Any, Dict

from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import (
    BooleanData,
    DecimalData,
    IntegerData,
    StringData,
)


def register_sources(graph: NodeGraph):
    graph.register_nodes(
        [BooleanSourceNode, IntegerSourceNode, FloatSourceNode, StringSourceNode]
    )


class BooleanSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Boolean Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_checkbox("in_cb", "", "Value", False)
        self.add_typed_output(BooleanData, name="Out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"Out": self.get_property("in_cb")}


class IntegerSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Integer Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_text_input("in_text", "", "0", "Integer val here")
        self.add_typed_output(IntegerData, name="Out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = self.get_property("in_text")
        value = value if isinstance(value, str) else ""

        return {"Out": IntegerData.parse(value) if IntegerData.validate(value) else 0}


class FloatSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "Float Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_text_input("in_text", "", "0.0", "Float val here")
        self.add_typed_output(DecimalData, name="Out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = self.get_property("in_text")
        value = value if isinstance(value, str) else ""

        return {
            "Out": (DecimalData.parse(value) if DecimalData.validate(value) else 0.0)
        }


class StringSourceNode(CustomNode):
    __identifier__ = "io.github.pastalapate.sources"

    NODE_NAME = "String Source"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_text_input("in_text", "", "", "Text here")
        self.add_typed_output(StringData, name="Out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = self.get_property("in_text")
        value = value if isinstance(value, str) else ""

        return {
            "Out": (StringData.parse(value) if StringData.validate(value) else "0.0")
        }
