from typing import Any, Dict

from NodeGraphQt import NodeBaseWidget, NodeGraph
from PySide6.QtWidgets import QWidget
from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import Color, ColorData, IntegerData


def register_colors(graph: NodeGraph):
    graph.register_nodes([ColorFromInts])


class DisplayColorNodeWidget(NodeBaseWidget):
    def __init__(
        self, parent=None, name=None, label="", default=Color(r=255, g=255, b=255)
    ):
        super().__init__(parent, name, label)
        self._wcolor = QWidget()
        self._wcolor.setMinimumSize(25, 25)
        self._color = default
        self._set_color(default)

        self.set_custom_widget(self._wcolor)

    def _set_color(self, color: Color):
        self._wcolor.setStyleSheet(
            f"QWidget {{ background-color: rgb({color['r']}, {color['g']}, {color['b']}); }}"
        )

    def set_value(self, color: Color):
        self._set_color(color)
        self._color = color

    def get_value(self):
        return self._color


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
