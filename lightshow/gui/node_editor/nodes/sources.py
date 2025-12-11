from typing import Any, Dict
from PySide6.QtWidgets import QCheckBox
from lightshow.gui.node_editor.custom_node import CustomNode

from lightshow.gui.node_editor.datas import BooleanData


class BooleanNodeDataModel(CustomNode):
    __identifier__ = "io.github.pastalapate"

    NODE_NAME = "Boolean Test"

    def __init__(self):

        super(BooleanNodeDataModel, self).__init__()
        self.add_checkbox('in_cb', '', "Out", False)
        self.add_typed_output(BooleanData, name="bool_out")
    
    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"bool_out": self.get_property("in_cb")}
    