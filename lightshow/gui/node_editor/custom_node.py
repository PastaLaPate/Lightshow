from typing import Type, TypeVar

from NodeGraphQt import BaseNode
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.errors import PortRegistrationError

from lightshow.gui.node_editor.datas import NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort

T = TypeVar("T")

"""Adapted from https://github.com/jchanvfx/NodeGraphQt"""


class CustomNode(BaseNode):
    def add_typed_input(
        self,
        data_type: Type[NodeDataType[T]],
        name: str = "input",
        multi_input=False,
        display_name=True,
        locked=False,
    ):
        if name in self.inputs().keys():
            raise PortRegistrationError(
                'port name "{}" already registered.'.format(name)
            )

        view = self.view.add_input(
            name=name, multi_port=multi_input, display_name=display_name, locked=locked
        )

        port = TypedPort(self, view, data_type)
        port.model.type_ = PortTypeEnum.IN.value
        port.model.name = name
        port.model.display_name = display_name
        port.model.multi_connection = multi_input
        port.model.locked = locked
        self._inputs.append(port)
        self.model.inputs[port.name()] = port.model
        return port

    def add_typed_output(
        self,
        data_type: Type[NodeDataType[T]],
        name="output",
        multi_output=False,
        display_name=True,
        locked=False,
    ):
        if name in self.outputs().keys():
            raise PortRegistrationError(
                'port name "{}" already registered.'.format(name)
            )

        view = self.view.add_output(
            name=name,
            multi_port=multi_output,
            display_name=display_name,
            locked=locked,
        )

        port = TypedPort(self, view, data_type)
        port.model.type_ = PortTypeEnum.OUT.value
        port.model.name = name
        port.model.display_name = display_name
        port.model.multi_connection = multi_output
        port.model.locked = locked
        self._outputs.append(port)
        self.model.outputs[port.name()] = port.model
        return port
