from typing import List, Type

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import GenericData, NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort


def resolve_component_type(start_port: TypedPort) -> Type[NodeDataType]:
    visited_ports = set()
    found_types = set()
    stack = [start_port]

    while stack:
        port = stack.pop()
        if port in visited_ports:
            continue
        visited_ports.add(port)

        if port.data_type != GenericData:
            found_types.add(port.data_type)

        for connected in port.connected_ports():
            stack.append(connected)
    if len(found_types) == 0:
        return GenericData
    if len(found_types) > 1:
        raise TypeError("More than one generic type found")

    return next(iter(found_types))


def collect_generic_nodes(start_port: TypedPort) -> set["GenericNode"]:
    visited_ports = set()
    nodes = set()
    stack = [start_port]
    while stack:
        port = stack.pop()
        if port in visited_ports:
            continue
        visited_ports.add(port)

        node = port.node()
        if isinstance(node, GenericNode):
            nodes.add(node)
        for connected in port.connected_ports():
            stack.append(connected)
    return nodes


def update_generic_component(start_port: TypedPort):
    resolved_type = resolve_component_type(start_port)
    nodes = collect_generic_nodes(start_port)
    for node in nodes:
        node.apply_resolved_type(resolved_type)


class GenericNode(CustomNode):
    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self._data_type = GenericData
        self.generic_input_ports: List[TypedPort] = []
        self.generic_output_ports: List[TypedPort] = []

    def on_input_connected(self, in_port, out_port):
        if isinstance(in_port, TypedPort):
            update_generic_component(in_port)

    def on_input_disconnected(self, in_port, out_port):
        if isinstance(in_port, TypedPort):
            update_generic_component(in_port)

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

    def apply_resolved_type(self, data_type: Type[NodeDataType]):
        for port in self.generic_input_ports:
            port.data_type = data_type
        for port in self.generic_output_ports:
            port.data_type = data_type

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
