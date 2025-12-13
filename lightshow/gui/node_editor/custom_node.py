from abc import ABC, abstractmethod
from typing import Any, Dict, Set, Type, TypeVar

from NodeGraphQt import BaseNode, NodeBaseWidget
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.errors import PortRegistrationError
from NodeGraphQt.widgets.node_widgets import NodeButton
from PySide6.QtWidgets import QLabel

from lightshow.gui.node_editor.datas import NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort, TypedPortItem

T = TypeVar("T")

"""Adapted from https://github.com/jchanvfx/NodeGraphQt"""


class CustomNode(BaseNode, ABC):

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self._cache = None  # stores the last computed output
        self._dirty = True  # must be recomputed
        """
        self.input_port_connected.connect(lambda *args: self.mark_dirty())
        self.property_changed.connect(lambda *args: self.mark_dirty())"""

    def generate_typed_port(
        self,
        port_type: PortTypeEnum,
        data_type: Type[NodeDataType[T]],
        name: str = "input",
        multi=False,
        display_name=True,
        locked=False,
    ):
        view = TypedPortItem(data_type, self._view)
        view.name = name
        view.port_type = port_type.value
        view.multi_connection = multi
        view.display_name = display_name
        view.locked = locked
        return self._view._add_port(view)

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

        view = self.generate_typed_port(
            PortTypeEnum.IN,
            data_type,
            name,
            multi_input,
            display_name,
            locked,
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

        view = self.generate_typed_port(
            PortTypeEnum.OUT,
            data_type,
            name,
            multi_output,
            display_name,
            locked,
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

    def _safe_compute(self, visited: Set["CustomNode"]) -> Dict[str, Any]:
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

    def _evaluate_input_port(self, port: TypedPort, visited: Set["CustomNode"]):
        """Return value from what this input port is connected to."""
        conns = port.connected_ports()
        if not conns:
            return port.data_type.default_value

        src_port = conns[0]
        src_node = src_port.node()

        # only CustomNode supports evaluation
        if not isinstance(src_node, CustomNode):
            return port.data_type.default_value

        if not isinstance(src_port, TypedPort):
            return port.data_type.default_value

        upstream_output = src_node._safe_compute(visited)

        # If upstream has 1 output, use that value
        out = (
            next(iter(upstream_output.values()))
            if len(upstream_output) == 1
            else upstream_output.get(src_port.name(), None)
        )
        return out if out is not None else src_port.data_type.default_value

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


class DisplayNodeWidget(NodeBaseWidget):
    def __init__(self, parent=None, name=None, label="", default=""):
        super().__init__(parent, name, label)
        self._wlabel = QLabel(default)
        self._wlabel.setMinimumSize(100, 25)
        self.set_custom_widget(self._wlabel)

    def set_value(self, text):
        self._wlabel.setText(text)

    def get_value(self):
        return self._wlabel.text()


class DisplayNode(CustomNode, ABC):

    __identifier__ = "io.github.pastalapate.displays"
    DATA_TYPE: Type[NodeDataType]

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.v_in = self.add_typed_input(
            data_type=self.DATA_TYPE,
            name=self.DATA_TYPE.name + " In",
            multi_input=False,
            display_name=True,
        )

        widget = DisplayNodeWidget(
            self._view,
            "display",
            "Result",
            self.DATA_TYPE.value_as_text(self.DATA_TYPE.default_value),
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
        key = self.DATA_TYPE.name + " In"
        value = inputs.get(key, None)
        text = self.DATA_TYPE.value_as_text("" if value is None else value)
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
