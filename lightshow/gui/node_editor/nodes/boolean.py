from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import BooleanData
from NodeGraphQt import NodeGraph


def register_gates(graph: NodeGraph):
    graph.register_nodes([OrGate, AndGate, XorGate])


class LogicGate(CustomNode):
    __identifier__ = "io.github.pastalapate.math.gates"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(BooleanData, "X", False)
        self.add_typed_input(BooleanData, "Y", False)
        self.add_typed_output(BooleanData, "Out", True)


class OrGate(LogicGate):
    NODE_NAME = "Or Gate"

    def compute(self, inputs):
        return {"Out": inputs["X"] or inputs["Y"]}


class AndGate(LogicGate):
    NODE_NAME = "And Gate"

    def compute(self, inputs):
        return {"Out": inputs["X"] and inputs["Y"]}


class XorGate(LogicGate):
    NODE_NAME = "Xor Gate"

    def compute(self, inputs):
        a = inputs["X"]
        b = inputs["Y"]
        return {"Out": (a and (not b)) or (b and (not a))}
