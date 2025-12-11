from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Type, TypeVar

from NodeGraphQt import BaseNode, Port
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.errors import PortRegistrationError
from NodeGraphQt.base.port import PortModel

from lightshow.gui.node_editor.datas import NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort

T = TypeVar("T")

"""Adapted from https://github.com/jchanvfx/NodeGraphQt"""


class CustomNode(BaseNode, ABC):

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self._cache = None          # stores the last computed output
        self._dirty = True          # must be recomputed
        """
        self.input_port_connected.connect(lambda *args: self.mark_dirty())
        self.property_changed.connect(lambda *args: self.mark_dirty())"""

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
    
    def evaluate(self) -> Dict[str, Any]:
        """Safely compute this node’s outputs."""
        return self._safe_compute(set())

    @abstractmethod
    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement in your custom node.
        Must return dict:
            {output_port_name: value}
        """
        raise NotImplementedError
    
    def _safe_compute(self, visited: Set['CustomNode']) -> Dict[str, Any]:
        # cycle detection
        if self in visited:
            raise RuntimeError(f"Cycle detected at node '{self.name()}'!")
        visited.add(self)

        # return cached result if clean
        if not self._dirty and self._cache is not None:
            return self._cache

        # gather inputs
        inputs: Dict[str, Any] = {}
        for port in self.inputs().values():
            upstream_value = self._evaluate_input_port(port, visited)
            inputs[port.name()] = upstream_value

        # compute this node
        output = self.compute(inputs)

        # cache
        self._cache = output
        self._dirty = False
        return output
    
    def _evaluate_input_port(self, port: Port, visited: Set['CustomNode']):
        """Return value from what this input port is connected to."""
        conns = port.connected_ports()
        if not conns:
            return None

        src_port = conns[0]
        src_node = src_port.node()

        # only CustomNode supports evaluation
        if not isinstance(src_node, CustomNode):
            return None

        upstream_output = src_node._safe_compute(visited)

        # If upstream has 1 output, use that value
        if len(upstream_output) == 1:
            return next(iter(upstream_output.values()))

        # Otherwise match output port by name
        return upstream_output.get(src_port.name(), None)

    def mark_dirty(self):
        """Call this whenever parameters or ports change."""
        if not self._dirty:
            self._dirty = True
            # Propagate dirtiness downstream
            for port in self.outputs().values():
                for other in port.connected_ports():
                    node = other.node()
                    if isinstance(node, CustomNode):
                        node.mark_dirty()