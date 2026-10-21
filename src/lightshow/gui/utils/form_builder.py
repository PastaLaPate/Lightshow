import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from PySide6.QtGui import QColor

from lightshow.gui.components.color_picker import ColorPicker
from lightshow.gui.components.path_selector import PathSelector
from lightshow.gui.components.validating_lineedit import ValidatingLineEdit

if sys.version_info >= (3, 15):
    from typing import TypeForm
else:
    from typing_extensions import TypeForm

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
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

        type_ = unwrap(info.annotation)

        if instance is not None:
            value = getattr(instance, name)
        else:
            value = info.get_default(call_default_factory=True)
            if value is PydanticUndefined:
                value = None
        specs.append(FieldSpec(name, type_, value, extras, constraints))
    return specs


class BaseFieldFactory[T, W: QWidget](ABC):
    @abstractmethod
    def construct(self, spec: FieldSpec, on_changed: Callable[[T], None]) -> W: ...

    @abstractmethod
    def apply_value(self, widget: W, value: T) -> None: ...

    def set_value(self, widget: W, value: T) -> None:
        with QSignalBlocker(widget):
            self.apply_value(widget, value)  # Avoid signal loop

    def set_locked(self, widget: W, locked: bool) -> None:
        widget.setEnabled(not locked)


class RangedNumberFactory[T: float | int, W: QWidget](BaseFieldFactory[T, W]):
    def initial(self, value: float | None, lo: float, hi: float) -> float | int:
        return value if value is not None else min(max(0, lo), hi)


class CheckBoxFactory(BaseFieldFactory[bool, QCheckBox]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[bool], None]
    ) -> QCheckBox:
        w = QCheckBox()
        w.setChecked(bool(spec.value))
        w.toggled.connect(on_changed)
        return w

    def apply_value(self, widget: QCheckBox, value: bool):
        widget.setChecked(value)


class SpinnerFactory(RangedNumberFactory[int, QSpinBox]):
    def construct(self, spec: FieldSpec, on_changed: Callable[[int], None]) -> QSpinBox:
        c = spec.constraints
        w = QSpinBox()
        # Use GT (exclusive) or GE (inclusive) for minimum
        min_val = c.get("gt", c.get("ge", -(2**31)))
        if isinstance(min_val, float):
            min_val = int(min_val)
        # If GT is set, add 1 to make it exclusive for integers
        if "gt" in c:
            min_val += 1
        w.setRange(min_val, c.get("le", c.get("lt", 2**31 - 1)))
        w.setValue(int(self.initial(spec.value, w.minimum(), w.maximum())))
        w.valueChanged.connect(on_changed)
        return w

    def apply_value(self, widget: QSpinBox, value: int):
        widget.setValue(value)


class FloatFactory(RangedNumberFactory[float, QDoubleSpinBox]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[float], None]
    ) -> QDoubleSpinBox:
        c = spec.constraints
        w = QDoubleSpinBox()
        # Use GT (exclusive) or GE (inclusive) for minimum
        min_val = c.get("gt", c.get("ge", -1e12))
        w.setRange(min_val, c.get("le", c.get("lt", 1e12)))
        w.setDecimals(4)
        w.setValue(self.initial(spec.value, w.minimum(), w.maximum()))
        w.valueChanged.connect(on_changed)
        return w

    def apply_value(self, widget: QDoubleSpinBox, value: float):
        widget.setValue(value)


class BarFactory(RangedNumberFactory[float | int, NumericSliderSpinBox]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[float | int], None]
    ) -> NumericSliderSpinBox:
        c = spec.constraints
        w = NumericSliderSpinBox(self._get_min(c), self._get_max(c))
        w.setValue(self.initial(spec.value, w.min, w.max))
        w.valueChanged.connect(on_changed)
        return w

    def _get_min(self, c: dict) -> float | int:
        # Use GT (exclusive) or GE (inclusive) for minimum
        min_val = c.get("gt", c.get("ge", 0))
        if isinstance(min_val, float):
            min_val = int(min_val)
        # If GT is set, add 1 to make it exclusive for integers
        if "gt" in c:
            min_val += 1
        return min_val

    def _get_max(self, c: dict) -> float | int:
        # Use LT (exclusive) or LE (inclusive) for maximum
        max_val = c.get("lt", c.get("le", 100))
        if isinstance(max_val, float):
            max_val = int(max_val)
        # If LT is set, subtract 1 to make it exclusive for integers
        if "lt" in c:
            max_val -= 1
        return max_val

    def apply_value(self, widget: NumericSliderSpinBox, value: float):
        widget.setValue(value)


class LineEditFactory(BaseFieldFactory[str, ValidatingLineEdit]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[str], None]
    ) -> ValidatingLineEdit:
        w = ValidatingLineEdit(spec.value or "", spec.extras.validation_scheme)
        w.setPlaceholderText(spec.extras.placeholder or "")
        if "max_length" in spec.constraints:
            w.setMaxLength(spec.constraints["max_length"])
        w.committed.connect(lambda new: on_changed(new))
        return w

    def apply_value(self, widget: ValidatingLineEdit, value: str):
        widget.setText(value)


class ColorPickerFactory(BaseFieldFactory[str, ColorPicker]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[str], None]
    ) -> ColorPicker:
        w = ColorPicker(QColor(spec.value))
        w.color_changed.connect(on_changed)
        return w

    def apply_value(self, widget: ColorPicker, value: str):
        widget.setColor(QColor(value))


class PathSelectorFactory(BaseFieldFactory[str, PathSelector]):
    def construct(
        self, spec: FieldSpec, on_changed: Callable[[str], None]
    ) -> PathSelector:
        # Extract file selector parameters from extras
        title = spec.extras.file_selector_title or "Select File or Directory"
        file_mode = spec.extras.file_selector_file_mode
        options = spec.extras.file_selector_options
        default_path = spec.extras.file_selector_default_path or spec.value or ""
        filters = spec.extras.file_selector_filters or []

        w = PathSelector(
            path=default_path,
            title=title,
            file_mode=file_mode,
            options=options,
            filters=filters,
        )
        w.path_changed.connect(on_changed)
        return w

    def apply_value(self, widget: PathSelector, value: str):
        widget.setPath(value)


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
            (str, WidgetType.ColorPicker): ColorPickerFactory(),
            (str, WidgetType.FileSelector): PathSelectorFactory(),
        }

    def resolve(self, spec: FieldSpec) -> BaseFieldFactory[Any, Any]:
        widget = spec.extras.widget
        if widget is None:
            return self.by_type[spec.type]
        try:
            return self.by_widget[(spec.type, widget)]
        except KeyError:
            raise ValueError(
                f"No factory found for {spec.type} with {spec.extras.widget}"
            )


@dataclass
class FormField:
    spec: FieldSpec
    widget: QWidget
    value: Any
    lock: Callable[[bool], None]
    set_value: Callable[[Any], None]


class ModelForm(QWidget):
    field_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = FieldFactoryRegistry()
        self.fields: dict[str, FormField] = {}

        self.form_layout = QFormLayout()
        self.setLayout(self.form_layout)

    def construct[T: BaseModel](self, model: type[T], instance: T | None):
        self.fields.clear()

        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)

        specs = inspect_model(model, instance)
        print(specs)
        for spec in specs:
            factory: BaseFieldFactory[Any, Any] = self.registry.resolve(spec)
            w = factory.construct(spec, partial(self._on_field_changed, spec.name))
            self.fields[spec.name] = FormField(
                spec,
                w,
                spec.value,
                partial(factory.set_locked, w),
                partial(factory.set_value, w),
            )
            self.form_layout.addRow(spec.extras.label, w)

    def set_connected(self, connected: bool):
        for f in self.fields.values():
            if f.spec.connected_readonly:
                f.lock(connected)

    def set_field(self, name: str, value: Any):
        self.fields[name].set_value(value)

    def _on_field_changed(self, name: str, value: Any):
        self.set_field(name, value)
        self.field_changed.emit(name, value)
