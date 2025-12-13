from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import DisplayNode
from lightshow.gui.node_editor.datas import (
    BooleanData,
    DecimalData,
    IntegerData,
    StringData,
)


def register_displays(graph: NodeGraph):
    graph.register_nodes([BooleanDisplay, IntegerDisplay, FloatDisplay, StringDisplay])


class BooleanDisplay(DisplayNode):
    NODE_NAME = "Boolean Display"
    DATA_TYPE = BooleanData


class IntegerDisplay(DisplayNode):
    NODE_NAME = "Integer Display"
    DATA_TYPE = IntegerData


class FloatDisplay(DisplayNode):
    NODE_NAME = "Float Display"
    DATA_TYPE = DecimalData


class StringDisplay(DisplayNode):
    NODE_NAME = "String Display"
    DATA_TYPE = StringData
