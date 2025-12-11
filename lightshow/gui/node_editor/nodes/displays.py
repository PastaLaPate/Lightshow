from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import DisplayNode
from lightshow.gui.node_editor.datas import BooleanData, DecimalData, IntegerData


def register_displays(graph: NodeGraph):
    graph.register_nodes([BooleanDisplay, IntegerDisplay, FloatDisplay])


class BooleanDisplay(DisplayNode):
    NODE_NAME = "Boolean Display"

    __identifier__ = "io.github.pastalapate.displays"
    DATA_TYPE = BooleanData


class IntegerDisplay(DisplayNode):
    NODE_NAME = "Integer Display"
    __identifier__ = "io.github.pastalapate.displays"
    DATA_TYPE = IntegerData


class FloatDisplay(DisplayNode):
    NODE_NAME = "Float Display"
    __identifier__ = "io.github.pastalapate.displays"
    DATA_TYPE = DecimalData
