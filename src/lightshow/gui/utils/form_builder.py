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
from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from lightshow.devices.fields import FieldExtras, WidgetType
from lightshow.gui.components.numeric_slider_spinbox import NumericSliderSpinBox

SECTION_QSS = """
#rootForm {
    background: #1a1a1a;
    border-radius: 8px;
}
#sectionHeader {
    border: none; text-align: left; padding: 4px 6px; font-weight: 600;
    color: #d0d0d0;
    background: #2b2b2b;
    border-radius: 4px;
}
#sectionHeader[level="0"] { background: #303030; }
#sectionHeader:hover { background: #363636; }
#sectionContent { border: none; background: transparent; }

QLabel { color: #b5b5b5; background: transparent; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #0f0f0f;
    color: #d0d0d0;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #0070e0;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #0070e0;
}
"""


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
        title = spec.extras.file_selector_title
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


class CollapsibleSection(QWidget):
    toggled = Signal(bool)

    def __init__(self, title: str, level: int = 0, expanded: bool = True, parent=None):
        super().__init__(parent)

        self.setObjectName("section")

        self.header = QToolButton()
        self.header.setObjectName("sectionHeader")
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.header.setProperty("level", level)
        self.header.toggled.connect(self._on_toggled)

        self.content = QFrame()
        self.content.setObjectName("sectionContent")

        body = QVBoxLayout(self.content)
        body.setContentsMargins(12 if level else 6, 4, 4, 4)
        body.setSpacing(2)

        self.form = QFormLayout()  # section's fields
        self.form.setContentsMargins(0, 0, 0, 0)
        body.addLayout(self.form)

        self.children_layout = QVBoxLayout()
        self.children_layout.setContentsMargins(0, 0, 0, 0)
        body.addLayout(self.children_layout)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addWidget(self.content)

        self._on_toggled(expanded)

    def _on_toggled(self, expanded: bool):
        self.header.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.content.setVisible(expanded)
        self.toggled.emit(expanded)


class ModelForm(QWidget):
    field_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rootForm")

        self.registry = FieldFactoryRegistry()
        self.fields: dict[str, FormField] = {}
        self._sections: dict[tuple[str, ...], CollapsibleSection] = {}
        self._expanded: dict[
            tuple[str, ...], bool
        ] = {}  # Save if the device gets re-selected

        self.setStyleSheet(SECTION_QSS)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 8, 8, 8)

        self._content: QWidget | None = None
        self._root_layout: QVBoxLayout | None = None

    def construct[T: BaseModel](self, model: type[T], instance: T | None) -> None:
        self._reset()

        specs = inspect_model(model, instance)
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
            cat = spec.extras.category
            path = tuple(p.strip() for p in cat.split("/"))
            self._section(path).form.addRow(spec.extras.label, w)
        if self._root_layout is not None:
            self._root_layout.addStretch(1)

    def _reset(self) -> None:
        self.fields.clear()
        self._sections.clear()

        if self._content is not None:
            self._content.setParent(None)
            self._content.deleteLater()

        self._content = QWidget()
        self._root_layout = QVBoxLayout(self._content)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(2)

        self._outer.addWidget(self._content)

    def _section(self, path: tuple[str, ...]) -> CollapsibleSection:
        if path in self._sections:
            return self._sections[path]

        parent_layout = (
            self._section(path[:-1]).children_layout
            if len(path) > 1
            else self._root_layout
        )  # Recursively find parent
        if parent_layout is None:
            raise RuntimeError("Wasnt initialized.")
        sec = CollapsibleSection(
            path[-1], level=len(path) - 1, expanded=self._expanded.get(path, True)
        )
        sec.toggled.connect(lambda e, p=path: self._expanded.__setitem__(p, e))
        parent_layout.addWidget(sec)
        self._sections[path] = sec
        return sec

    def set_connected(self, connected: bool) -> None:
        for f in self.fields.values():
            if f.spec.connected_readonly:
                f.lock(connected)

    def set_field(self, name: str, value: Any) -> None:
        self.fields[name].set_value(value)

    def _on_field_changed(self, name: str, value: Any) -> None:
        self.set_field(name, value)
        self.field_changed.emit(name, value)
