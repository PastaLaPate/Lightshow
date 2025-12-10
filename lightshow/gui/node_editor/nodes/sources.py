from PySide6.QtWidgets import QCheckBox
from qtpy.QtWidgets import QWidget
from qtpynodeeditor import NodeDataModel, PortType

from lightshow.gui.node_editor.datas import BooleanData


class BooleanNodeDataModel(NodeDataModel):
    name = "Boolean Source"
    caption_visible = False
    num_ports = {
        PortType.input: 0,
        PortType.output: 1,
    }
    port_caption = {"output": {0: "Output"}}
    data_type = BooleanData.data_type

    def __init__(self, style=None, parent=None):
        super().__init__(style, parent)
        self._value = False
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(False)

    @property
    def value(self) -> bool:
        return self._value

    def embedded_widget(self) -> QWidget:
        return self.checkbox

    def on_checkbox_toggled(self, state):
        self._value = state
        self.data_updated.emit(0)
