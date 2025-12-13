from typing import Type, TypeVar

from NodeGraphQt import Port
from NodeGraphQt.qgraphics.port import PortItem

from lightshow.gui.node_editor.datas import NodeDataType

T = TypeVar("T")


class TypedPortItem(PortItem):
    def __init__(self, data_type: Type[NodeDataType[T]], parent=None):
        super().__init__(parent)
        self._data_type = data_type


class TypedPort(Port):
    def __init__(self, node, port: TypedPortItem, data_type: Type[NodeDataType[T]]):
        # Color conversion from hell
        port.color = (
            *tuple(int(data_type.color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)),
            255,
        )  # Hex to rgb + 255 for alpha
        super().__init__(node, port)
        self.data_type = data_type

    def connect_to(self, port=None, push_undo=True, emit_signal=True):
        if not isinstance(port, TypedPort):
            raise TypeError("Can only connect to another TypedPort")
        if self.data_type != port.data_type:
            return
        return super().connect_to(port, push_undo, emit_signal)
