from typing import Any, Dict

from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import IntegerData, StringData


def register_string_operations(graph: NodeGraph):
    graph.register_nodes([ConcenateStrings, StringLen])


class ConcenateStrings(CustomNode):
    NODE_NAME = "Concenate Strings"
    __identifier__ = "io.github.pastalapate.strings"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(StringData, "In 1")
        self.add_typed_input(StringData, "In 2")
        self.add_typed_output(StringData, "Out", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"Out": inputs["In 1"] + inputs["In 2"]}


class StringLen(CustomNode):
    NODE_NAME = "String len"
    __identifier__ = "io.github.pastalapate.strings"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(StringData, "In")
        self.add_typed_output(IntegerData, "Len", multi_output=True)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"Len": len(inputs["In"])}


class InString(CustomNode):
    NODE_NAME = "In string"
    __identifier__ = "io.github.pastalapate.strings"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(StringData, "Find string x")
        self.add_typed_input(StringData, "In string y")
