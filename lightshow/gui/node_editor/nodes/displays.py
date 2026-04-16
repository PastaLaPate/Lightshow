from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.display_node import DisplayNode
from lightshow.gui.node_editor.datas import (
    ColorData,
)
from lightshow.gui.node_editor.nodes.colors import DisplayColorNodeWidget


def register_displays(graph: NodeGraph):
    graph.register_nodes(
        [
            DisplayNode,
            ColorDisplay,
        ]
    )


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
