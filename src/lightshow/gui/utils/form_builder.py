from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QLineEdit, QSpinBox, QWidget

from lightshow.devices.fields import FieldExtras, WidgetType
from lightshow.gui.components.numeric_slider_spinbox import NumericSliderSpinBox


@dataclass
class FieldSpec:
    name: str
    type: Any
    value: Any
    extras: FieldExtras
    constraints: dict[str, Any] = field(default_factory=dict)

    @property
    def widget_hint(self) -> str | None:
        return self.extras.widget

    @property
    def connected_readonly(self) -> bool:
        return self.extras.connected_readonly


def inspect_model(model: type[BaseModel], instance=None) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    name: str
    info: FieldInfo
    for name, info in model.model_fields.items():
        constraints = {  # dict comprehension are from another planet
            k: getattr(m, k)
            for m in info.metadata
            for k in ("ge", "gt", "le", "lt", "max_length")
            if getattr(m, k, None) is not None
        }
        value = (
            getattr(instance, name)
            if instance
            else info.get_default(call_default_factory=True)
        )
        extras = FieldExtras.model_validate(
            (info.json_schema_extra or {}).get("ui", {})
        )
        specs.append(FieldSpec(name, info.annotation, value, extras, constraints))
    return specs


class BaseFieldFactory[T](ABC):
    @abstractmethod
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[T], None]
    ) -> QWidget: ...

    def set_locked(self, widget: QWidget, locked: bool) -> None:
        widget.setEnabled(not locked)


class CheckBoxFactory(BaseFieldFactory[bool]):
    def construct(self, spec: FieldSpec, on_changed: Callable[[bool], None]) -> QWidget:
        w = QCheckBox()
        w.setChecked(bool(spec.value))
        w.toggled.connect(on_changed)
        return w


class SpinnerFactory(BaseFieldFactory[int]):
    def construct(self, spec: FieldSpec, on_changed: Callable[[int], None]) -> QWidget:
        c = spec.constraints
        w = QSpinBox()
        w.setRange(c.get("ge", -(2**31)), c.get("le", 2**31 - 1))
        w.setValue(spec.value)
        w.valueChanged.connect(on_changed)
        return w


class FloatFactory(BaseFieldFactory[float]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[float], None]
    ) -> QWidget:
        c = spec.constraints
        w = QDoubleSpinBox()
        w.setRange(c.get("ge", -1e12), c.get("le", 1e12))
        w.setDecimals(4)
        w.setValue(spec.value)
        w.valueChanged.connect(on_changed)
        return w


class BarFactory(BaseFieldFactory[float | int]):
    def construct(self, spec: FieldSpec, on_changed: Callable[[float | int], None]):
        c = spec.constraints
        w = NumericSliderSpinBox(c.get("ge", 0), c.get("le", 100))
        w.setValue(spec.value)
        w.valueChanged.connect(on_changed)
        return w


class LineEditFactory(BaseFieldFactory[str]):
    def construct(self, spec: FieldSpec, on_changed: Callable[[str], None]):
        w = QLineEdit(spec.value or "")
        if "max_length" in spec.constraints:
            w.setMaxLength(spec.constraints["max_length"])
        w.textChanged.connect(on_changed)
        return w


class FieldFactoryRegistry:
    def __init__(self):
        self.by_type: dict[type, BaseFieldFactory] = {
            bool: CheckBoxFactory(),
            str: LineEditFactory(),
            int: SpinnerFactory(),
            float: FloatFactory(),
        }

        self.by_widget_type: dict[WidgetType, BaseFieldFactory] = {
            WidgetType.Checkbox: CheckBoxFactory(),
            WidgetType.Spinner: FloatFactory(),
            WidgetType.Field: LineEditFactory(),
            WidgetType.Slider: BarFactory(),
            # WidgetType.ColorPicker:
        }

    def resolve(self, spec: FieldSpec) -> BaseFieldFactory:
        if spec.extras.widget in self.by_widget_type:
            return self.by_widget_type[spec.extras.widget]
        return self.by_type[spec.type]
