from typing import Any
from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import DisplayNode
from lightshow.gui.node_editor.datas import (
    ArrayData,
    BooleanData,
    ColorData,
    DecimalData,
    IntegerData,
    StringData,
)
from lightshow.gui.node_editor.nodes.colors import DisplayColorNodeWidget


def register_displays(graph: NodeGraph):
    graph.register_nodes(
        [
            BooleanDisplay,
            IntegerDisplay,
            FloatDisplay,
            StringDisplay,
            ColorDisplay,
            ArrayDisplay,
        ]
    )


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


class ColorDisplay(DisplayNode):
    NODE_NAME = "Color Display"
    DATA_TYPE = ColorData

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self._wcolor = DisplayColorNodeWidget(
            self._view, "color_display", "Color display", ColorData.default_value
        )
        self.add_custom_widget(self._wcolor)

    def compute(self, inputs):
        key = self.DATA_TYPE.name + " In"
        value = inputs.get(key, None)
        self._wcolor.set_value(value)
        return super().compute(inputs)


class ArrayDisplay(DisplayNode):
    NODE_NAME = "Array Display"
    DATA_TYPE = ArrayData[Any]
