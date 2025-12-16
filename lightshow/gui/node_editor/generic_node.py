from typing import List, Type
from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import GenericData, NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort


class GenericNode(CustomNode):
    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self._data_type = GenericData
        self.generic_input_ports: List[TypedPort] = []
        self.generic_output_ports: List[TypedPort] = []

    def on_input_connected(self, in_port, out_port):
        if not isinstance(in_port, TypedPort) or not isinstance(out_port, TypedPort):
            return

        if out_port.data_type == GenericData:
            out_port.node().data_type = self.data_type
        if self.data_type == GenericData:
            self.data_type = out_port.data_type
        if not out_port:
            self.data_type = GenericData

    def add_generic_input(
        self, name: str = "input", multi_input=False, display_name=True, locked=False
    ):
        port = self.add_typed_input(
            GenericData,
            name=name,
            multi_input=multi_input,
            display_name=display_name,
            locked=locked,
        )
        self.generic_input_ports.append(port)

    def add_generic_output(
        self, name: str = "output", multi_output=True, display_name=True, locked=False
    ):
        port = self.add_typed_output(
            GenericData,
            name=name,
            multi_output=multi_output,
            display_name=display_name,
            locked=locked,
        )
        self.generic_output_ports.append(port)

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, value: Type[NodeDataType]):
        self._data_type = value
        for in_port in self.generic_input_ports:
            in_port.data_type = value
        for out_port in self.generic_output_ports:
            out_port.data_type = value
