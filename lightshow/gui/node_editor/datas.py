from abc import ABC, abstractmethod
from typing import Generic, TypeVar

"""
DecimalType = NodeDataType(id="decimal", name="Decimal")
StringType = NodeDataType(id="string", name="String")
IntegerType = NodeDataType(id="integer", name="Integer")
ColorType = NodeDataType(id="color", name="Color")
ColorGradientType = NodeDataType(id="color_gradient", name="Color Gradient")
BooleanType = NodeDataType(id="boolean", name="Boolean")
AnimationType = NodeDataType(id="animation", name="Animation")
"""

T = TypeVar("T")


class NodeDataType(Generic[T], ABC):
    id: str
    name: str
    default_value: T

    color: str = "#FFFFFF"  # Default color for this data type in hex format

    @staticmethod
    @abstractmethod
    def value_as_text(value: T) -> str:
        pass

    @staticmethod
    @abstractmethod
    def validate(value: str) -> bool:
        return True

    @staticmethod
    @abstractmethod
    def parse(value: str) -> T:
        pass


class BooleanData(NodeDataType[bool]):
    default_value = False
    id = "boolean"
    name = "Boolean"
    color = "#FF5100"

    @staticmethod
    def value_as_text(value) -> str:
        return "True" if value else "False"

    @staticmethod
    def validate(value: str) -> bool:
        return value.lower() in ("true", "false") or value in ("1", "0")

    @staticmethod
    def parse(value: str) -> bool:
        return value.lower() == "true" or value == "1"


class DecimalData(NodeDataType[float]):
    default_value = 0.0
    id = "decimal"
    name = "Decimal"
    color = "#00FF15"

    @staticmethod
    def value_as_text(value) -> str:
        return "%g" % value

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


class IntegerData(NodeDataType[int]):
    default_value = 0
    id = "int"
    name = "Integer"
    color = "#0099FF"

    @staticmethod
    def integer_as_text(value) -> str:
        return str(value)

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
