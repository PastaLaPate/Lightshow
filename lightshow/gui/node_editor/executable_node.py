from typing import Any, Dict
from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import ExecData
from lightshow.gui.node_editor.typed_port import TypedPort


class ExecutableNode(CustomNode):
    def __init__(self, qgraphics_item=None, add_input=True, add_output=True):
        super().__init__(qgraphics_item)
        if add_input:
            self.exec_in = self.add_typed_input(ExecData, "exec_in", False, False)
        if add_output:
            self.exec_out = self.add_typed_output(ExecData, "exec_out", False, False)
        self.computed: Dict[str, Any] = {}

    def next(self):
        self._dirty = True
        self._cache = None
        self.computed = self.evaluate()
        if len(self.exec_out.connected_ports()) == 0:
            return
        next_port: TypedPort = self.exec_out.connected_ports()[0]
        next_node = next_port.node()
        if not isinstance(next_node, ExecutableNode):
            return
        next_node.next()

    def _evaluate_input_port(self, port, visited):
        """Return value from what this input port is connected to."""
        conns = port.connected_ports()
        if not conns:
            return port.data_type.default_value
        output_list = []
        for src_port in conns:
            src_node = src_port.node()

            # only CustomNode supports evaluation
            if not isinstance(src_node, CustomNode):
                return port.data_type.default_value

            if not isinstance(src_port, TypedPort):
                return port.data_type.default_value

            if isinstance(src_node, ExecutableNode):
                if src_port.data_type == ExecData:
                    continue
                out = src_node.computed[src_port.name()]
                output_list.append(out)
                continue

            upstream_output = src_node._safe_compute(visited)

            # If upstream has 1 output, use that value
            out = (
                next(iter(upstream_output.values()))
                if len(upstream_output) == 1
                else upstream_output.get(src_port.name(), None)
            )
            output_list.append(out)
        return (
            (output_list if len(output_list) > 1 else output_list[0])
            if len(output_list) > 0
            else port.data_type.default_value
        )
