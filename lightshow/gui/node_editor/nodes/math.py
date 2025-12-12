import math
import random
from typing import Any, Dict

from NodeGraphQt import NodeGraph

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import BooleanData, DecimalData, IntegerData


def register_math_nodes(graph: NodeGraph):
    graph.register_nodes(
        [
            IntToFloat,
            RoundNode,
            FloorNode,
            CeilNode,
            AddIntNode,
            SubIntNode,
            MulIntNode,
            ModIntNode,
            AddFloatNode,
            SubFloatNode,
            MulFloatNode,
            DivFloatNode,
            ModFloatNode,
            RandomFloatInRange,
            RandomIntInRange,
            RandomBoolean,
        ]
    )


def zero_safe(x: int):
    return 1 if x == 0 else x


class IntToFloat(CustomNode):
    __identifier__ = "io.github.pastalapate.math"
    NODE_NAME = "Int to float"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            IntegerData, name="in_int", multi_input=False, display_name=False
        )
        self.add_typed_output(
            DecimalData, name="out_float", multi_output=True, display_name=False
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out_float": float(inputs["in_int"])}


class RoundNode(CustomNode):
    __identifier__ = "io.github.pastalapate.math.round"
    NODE_NAME = "Round float"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            DecimalData, name="in_float", multi_input=False, display_name=False
        )
        self.add_typed_output(
            IntegerData, name="out_int", multi_output=True, display_name=False
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out_int": round(inputs["in_float"])}


class FloorNode(CustomNode):
    __identifier__ = "io.github.pastalapate.math.round"
    NODE_NAME = "Floor float"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            DecimalData, name="in_float", multi_input=False, display_name=False
        )
        self.add_typed_output(
            IntegerData, name="out_int", multi_output=True, display_name=False
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out_int": math.floor(inputs["in_float"])}


class CeilNode(CustomNode):
    __identifier__ = "io.github.pastalapate.math.round"
    NODE_NAME = "Ceil float"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            DecimalData, name="in_float", multi_input=False, display_name=False
        )
        self.add_typed_output(
            IntegerData, name="out_int", multi_output=True, display_name=False
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out_int": math.ceil(inputs["in_float"])}


class BaseIntMathNode(CustomNode):
    __identifier__ = "io.github.pastalapate.math.int"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            IntegerData, name="int_1", multi_input=False, display_name=False
        )
        self.add_typed_input(
            IntegerData, name="int_2", multi_input=False, display_name=False
        )
        self.add_typed_output(
            IntegerData, name="out", multi_output=True, display_name=True
        )


class AddIntNode(BaseIntMathNode):
    NODE_NAME = "Add Int"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["int_1"] + inputs["int_2"]}


class SubIntNode(BaseIntMathNode):
    NODE_NAME = "Sub Int"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["int_1"] - inputs["int_2"]}


class MulIntNode(BaseIntMathNode):
    NODE_NAME = "Mul Int"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["int_1"] * inputs["int_2"]}


class ModIntNode(BaseIntMathNode):
    NODE_NAME = "Mod Int"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["int_1"] % zero_safe(inputs["int_2"])}


class BaseFloatMathNode(CustomNode):
    __identifier__ = "io.github.pastalapate.math.float"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            DecimalData, name="float_1", multi_input=False, display_name=False
        )
        self.add_typed_input(
            DecimalData, name="float_2", multi_input=False, display_name=False
        )
        self.add_typed_output(
            DecimalData, name="out", multi_output=True, display_name=True
        )


class AddFloatNode(BaseFloatMathNode):
    NODE_NAME = "Add float"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["float_1"] + inputs["float_2"]}


class SubFloatNode(BaseFloatMathNode):
    NODE_NAME = "Sub float"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["float_1"] - inputs["float_2"]}


class MulFloatNode(BaseFloatMathNode):
    NODE_NAME = "Mul float"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["float_1"] * inputs["float_2"]}


class DivFloatNode(BaseFloatMathNode):
    NODE_NAME = "Div float"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["float_1"] / zero_safe(inputs["float_2"])}


class ModFloatNode(BaseFloatMathNode):
    NODE_NAME = "Mod float"

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": inputs["float_1"] % zero_safe(inputs["float_2"])}


class RandomFloatInRange(CustomNode):
    NODE_NAME = "Random Float in Range"
    __identifier__ = "io.github.pastalapate.math.random"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            DecimalData, name="Min", multi_input=False, display_name=True
        )
        self.add_typed_input(
            DecimalData, name="Max", multi_input=False, display_name=True
        )
        self.add_typed_output(
            DecimalData, name="out", multi_output=True, display_name=True
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": random.uniform(inputs["Min"], inputs["Max"])}


class RandomIntInRange(CustomNode):
    NODE_NAME = "Random Int in Range"
    __identifier__ = "io.github.pastalapate.math.random"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_input(
            IntegerData, name="Min", multi_input=False, display_name=True
        )
        self.add_typed_input(
            IntegerData, name="Max", multi_input=False, display_name=True
        )
        self.add_typed_output(
            IntegerData, name="out", multi_output=True, display_name=True
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": random.randint(inputs["Min"], inputs["Max"])}


class RandomBoolean(CustomNode):
    NODE_NAME = "Random Boolean"
    __identifier__ = "io.github.pastalapate.math.random"

    def __init__(self, qgraphics_item=None):
        super().__init__(qgraphics_item)
        self.add_typed_output(
            BooleanData, name="out", multi_output=True, display_name=True
        )

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"out": random.uniform(0, 1) > 0.5}
