from NodeGraphQt import NodeBaseWidget
from PySide6.QtWidgets import QLabel
from lightshow.gui.node_editor.custom_node import CustomNode


from NodeGraphQt.widgets.node_widgets import NodeButton


from abc import ABC
from typing import Any, Dict

from lightshow.gui.node_editor.generic_node import GenericNode


class DisplayNodeWidget(NodeBaseWidget):
    def __init__(self, parent=None, name=None, label="", default=""):
        super().__init__(parent, name, label)
        self._wlabel = QLabel(default)
        self._wlabel.setMinimumSize(100, 25)
        font = self._wlabel.font()
        font.setKerning(False)
        self._wlabel.setFont(font)
        self.set_custom_widget(self._wlabel)

    def set_value(self, text):
        self._wlabel.setText(text)

    def get_value(self):
        return self._wlabel.text()


class DisplayNode(GenericNode, ABC):
    __identifier__ = "io.github.pastalapate.displays"
    NODE_NAME = "Display"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.v_in = self.add_generic_input("In", False, False)

        widget = DisplayNodeWidget(
            self._view,
            "display",
            "Result",
            "",
        )
        self._label = widget._wlabel
        self.add_custom_widget(widget)
        self.add_button(
            name="force_recompute",
            label="Force Recompute",
            text="Force Recompute",
            tooltip="Click to recompute",
        )
        # Fixes saving issues
        self.create_property("force_recompute", "Force Recompute")

        button = self.get_widget("force_recompute")
        if isinstance(button, NodeButton):
            button.value_changed.connect(self.on_force_recompute)

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        value = inputs.get("In", None)
        text = "" if value is None else self._data_type.value_as_text(value)
        self._label.setText(text)
        return {}

    def on_force_recompute(self):
        # mark this node and whole upstream graph dirty
        def mark_upstream(node):
            if not isinstance(node, CustomNode):
                return
            node._dirty = True
            for port in node.inputs().values():
                for conn in port.connected_ports():
                    mark_upstream(conn.node())

        mark_upstream(self)
        # now re-evaluate
        try:
            self.evaluate()
        except RuntimeError:
            pass

    def mark_dirty(self):
        super().mark_dirty()
        # auto-refresh the shown value
        try:
            self.evaluate()
        except RuntimeError:
            pass
