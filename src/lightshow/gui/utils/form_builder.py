import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

if sys.version_info >= (3, 15):
    from typing import TypeForm
else:
    from typing_extensions import TypeForm

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

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
    def connected_readonly(self) -> bool:
        return self.extras.connected_readonly


def unwrap(tp: TypeForm[Any]) -> TypeForm[Any]:
    while True:
        origin = get_origin(tp)
        if origin is Annotated:
            tp = get_args(tp)[0]
        elif origin in (Union, UnionType):
            args = [a for a in get_args(tp) if a is not type(None)]
            if len(args) != 1:  # things like str | int, banned
                return tp
            tp = args[0]
        else:
            return tp


# TODO: Implement Greater exclusive (GT and LT)


def inspect_model[T: BaseModel](
    model: type[T], instance: T | None = None
) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    for name, info in model.model_fields.items():
        schema_extra = info.json_schema_extra
        if (
            not schema_extra
            or not isinstance(schema_extra, dict)
            or "ui" not in schema_extra
            or info.annotation is None
        ):
            continue

        extras = FieldExtras.model_validate(schema_extra["ui"])

        constraints = {  # dict comprehension are from another planet
            k: getattr(m, k)
            for m in info.metadata
            for k in ("ge", "gt", "le", "lt", "max_length")
            if getattr(m, k, None) is not None
        }

        if instance is not None:
            value = getattr(instance, name)
        else:
            value = info.get_default(call_default_factory=True)
            if value is PydanticUndefined:
                value = None
        specs.append(
            FieldSpec(name, unwrap(info.annotation), value, extras, constraints)
        )
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

        self.by_widget: dict[tuple[type, WidgetType], BaseFieldFactory] = {
            (int, WidgetType.Spinner): SpinnerFactory(),
            (float, WidgetType.Spinner): FloatFactory(),
            (int, WidgetType.Slider): BarFactory(),
            (float, WidgetType.Slider): BarFactory(),
            (bool, WidgetType.Checkbox): CheckBoxFactory(),
            (str, WidgetType.Field): LineEditFactory(),
            # WidgetType.ColorPicker:
        }

    def resolve(self, spec: FieldSpec) -> BaseFieldFactory[Any]:
        widget = spec.extras.widget
        if widget is None:
            return self.by_type[spec.type]
        try:
            return self.by_widget[(spec.type, widget)]
        except KeyError:
            raise ValueError(
                f"No factory found for {spec.type} with {spec.extras.widget}"
            )


class FormField(QObject):
    onChanged = Signal(object)

    def __init__(
        self, spec: FieldSpec, widget: QWidget, value: Any, lock: Callable[[bool], None]
    ):
        super().__init__()
        self.spec = spec
        self.widget: QWidget = widget
        self.value: Any = value
        self.lock: Callable[[bool], None] = lock


class ModelForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = FieldFactoryRegistry()
        self.fields: dict[str, FormField] = {}

        self.form_layout = QFormLayout()
        self.setLayout(self.form_layout)

    def construct[T: BaseModel](self, model: type[T], instance: T | None):
        self.fields.clear()

        while self.form_layout.rowCount() > 0:
            item = self.form_layout.takeRow(0)
            if item.fieldItem:
                item.fieldItem.widget().deleteLater()
            if item.labelItem:
                item.labelItem.widget().deleteLater()

        specs = inspect_model(model, instance)
        print(specs)
        for spec in specs:
            factory: BaseFieldFactory[Any] = self.registry.resolve(spec)
            w = factory.construct(spec, partial(self.field_changed, spec.name))
            self.fields[spec.name] = FormField(
                spec, w, spec.value, partial(factory.set_locked, w)
            )
            self.form_layout.addRow(spec.extras.label, w)

    def set_connected(self, connected: bool):
        for f in self.fields.values():
            if f.spec.connected_readonly:
                f.lock(connected)

    def field_changed(self, name, value):
        self.fields[name].value = value
        self.fields[name].onChanged.emit(value)
