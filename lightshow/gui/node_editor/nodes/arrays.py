from typing import Any, Type, TypeVar
from NodeGraphQt import NodeGraph
from lightshow.gui.node_editor.datas import (
    ArrayData,
    NodeDataType,
)
from lightshow.gui.node_editor.generic_node import GenericNode

T = TypeVar("T", bound=NodeDataType)


def register_arrays(graph: NodeGraph):
    graph.register_nodes([MakeArrayNode])


class MakeArrayNode(GenericNode):
    __identifier__ = "io.github.pastalapate.arrays"
    NODE_NAME = "Make Array"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_generic_input("Items", True)
        self.add_typed_output(
            data_type=ArrayData[Any],
            name="array",
        )

    @GenericNode.data_type.setter
    def data_type(self, value: Type[NodeDataType]):
        self._data_type = value
        for in_port in self.generic_input_ports:
            in_port.data_type = value
        self.output_ports()[0].data_type = ArrayData[type(value.default_value)]

    def compute(self, inputs):
        items = inputs.get("Items", [])

        # Normalize input to list
        if items is None:
            items = []
        elif not isinstance(items, list):
            items = [items]

        return {"array": items}
