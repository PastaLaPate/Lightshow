import threading
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from qtpynodeeditor import NodeData, NodeDataType

DecimalType = NodeDataType(id="decimal", name="Decimal")
StringType = NodeDataType(id="string", name="String")
IntegerType = NodeDataType(id="integer", name="Integer")
ColorType = NodeDataType(id="color", name="Color")
ColorGradientType = NodeDataType(id="color_gradient", name="Color Gradient")
BooleanType = NodeDataType(id="boolean", name="Boolean")
AnimationType = NodeDataType(id="animation", name="Animation")

T = TypeVar("T")


class CustomNodeData(NodeData, Generic[T], ABC):
    default_value: T
    data_type: NodeDataType

    def __init__(self, value: T) -> None:
        self._lock = threading.RLock()
        self._value = value

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def value(self) -> T:
        return self._value

    @abstractmethod
    def value_as_text(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def validate(value: str) -> bool:
        return True

    @staticmethod
    @abstractmethod
    def parse(value: str) -> T:
        pass


class BooleanData(CustomNodeData[bool]):
    data_type = BooleanType
    default_value = False

    def value_as_text(self) -> str:
        return "True" if self._value else "False"

    @staticmethod
    def validate(value: str) -> bool:
        return value.lower() in ("true", "false") or value in ("1", "0")

    @staticmethod
    def parse(value: str) -> bool:
        return value.lower() == "true" or value == "1"


class DecimalData(CustomNodeData[float]):
    data_type = DecimalType
    default_value = 0.0

    def value_as_text(self) -> str:
        return "%g" % self._value

    @staticmethod
    def validate(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def parse(value: str) -> float:
        return float(value)


class IntegerData(CustomNodeData[int]):
    data_type = IntegerType
    default_value = 0

    def integer_as_text(self) -> str:
        return str(self._value)

    @staticmethod
    def validate(value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def parse(value: str) -> int:
        return int(value)
