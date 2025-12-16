from typing import Type, TypeVar, get_origin, get_args, Any

from NodeGraphQt import Port
from NodeGraphQt.qgraphics.port import PortEnum, PortItem
from PySide6 import QtCore, QtGui

from lightshow.gui.node_editor.datas import GenericData, NodeDataType

T = TypeVar("T")


def _split_type(t):
    origin = get_origin(t) or t
    args = get_args(t)
    return origin, args


def _array_types_compatible(a, b):
    a_origin, a_args = _split_type(a)
    b_origin, b_args = _split_type(b)

    # Not the same container type
    if a_origin is not b_origin:
        return False

    # Non-generic container (ArrayData without args)
    if not a_args or not b_args:
        return True

    a_t = a_args[0]
    b_t = b_args[0]

    # Any matches everything
    if a_t is Any or b_t is Any:
        return True

    return a_t is b_t


class TypedPortItem(PortItem):
    def __init__(self, data_type: Type[NodeDataType[T]], parent=None):
        super().__init__(parent)
        self._data_type = data_type
        self._width = 33
        self._height = 33
        self._border_size = 6

    @PortItem.color.setter
    def color(self, color=(0, 0, 0, 255)):
        self._color = color
        self.update()

    @PortItem.locked.setter
    def locked(self, value=False):
        self._locked = value
        conn_type = "multi" if self._multi_connection else "single"
        tooltip = "{}: {} ({})".format(self.name, self._data_type.name, conn_type)
        if value:
            tooltip += " (L)"
        self.setToolTip(tooltip)

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, ndata_t: Type[NodeDataType[T]]):
        self._data_type = ndata_t
        conn_type = "multi" if self._multi_connection else "single"
        self.setToolTip(
            "{}: {} ({})".format(self.name, self._data_type.name, conn_type)
        )

    @PortItem.multi_connection.setter
    def multi_connection(self, mode):
        self._multi_connection = mode
        conn_type = "multi" if mode else "single"
        self.setToolTip(
            "{}: {} ({})".format(self.name, self._data_type.name, conn_type)
        )

    def paint(self, painter, option, widget):
        """
        Draws the circular port.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()

        #  display falloff collision for debugging
        # ----------------------------------------------------------------------
        # pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 80), 0.8)
        # pen.setStyle(QtCore.Qt.DotLine)
        # painter.setPen(pen)
        # painter.drawRect(self.boundingRect())
        # ----------------------------------------------------------------------

        rect_w = self._width / 1.8
        rect_h = self._height / 1.8
        rect_x = self.boundingRect().center().x() - (rect_w / 2)
        rect_y = self.boundingRect().center().y() - (rect_h / 2)
        port_rect = QtCore.QRectF(rect_x, rect_y, rect_w, rect_h)

        if self._hovered:
            color = QtGui.QColor(*PortEnum.HOVER_COLOR.value)
            border_color = QtGui.QColor(*PortEnum.HOVER_BORDER_COLOR.value)
        elif self.connected_pipes:
            color = QtGui.QColor(*self.color)
            border_color = QtGui.QColor(74, 84, 85, 255)
        else:
            color = QtGui.QColor(125, 125, 125, 255)
            border_color = QtGui.QColor(74, 84, 85, 255)

        pen = QtGui.QPen(border_color, self._border_size)
        painter.setPen(pen)
        painter.setBrush(border_color)
        painter.drawEllipse(port_rect)

        if not self._hovered:
            w = port_rect.width()
            h = port_rect.height()
            rect = QtCore.QRectF(
                port_rect.center().x() - w / 2, port_rect.center().y() - h / 2, w, h
            )
            pen = QtGui.QPen(color, 1.4)
            painter.setPen(pen)
            painter.setBrush(color)
            painter.drawEllipse(rect)
        elif self._hovered:
            if self.multi_connection:
                pen = QtGui.QPen(border_color, 1.4)
                painter.setPen(pen)
                painter.setBrush(color)
                w = port_rect.width() / 1.8
                h = port_rect.height() / 1.8
            else:
                painter.setBrush(border_color)
                w = port_rect.width() / 3.5
                h = port_rect.height() / 3.5
            rect = QtCore.QRectF(
                port_rect.center().x() - w / 2, port_rect.center().y() - h / 2, w, h
            )
            painter.drawEllipse(rect)
        painter.restore()


class TypedPort(Port):
    def __init__(self, node, port: TypedPortItem, data_type: Type[NodeDataType[T]]):
        # Color conversion from hell
        port.color = (
            *tuple(int(data_type.color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)),
            255,
        )  # Hex to rgb + 255 for alpha
        super().__init__(node, port)
        self.__view = port
        self._data_type = data_type

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, val: Type[NodeDataType[T]]):
        self._data_type = val
        self.__view.data_type = val
        self.__view.color = (
            *tuple(int(val.color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)),
            255,
        )

    def connect_to(self, port=None, push_undo=True, emit_signal=True):
        if not isinstance(port, TypedPort):
            raise TypeError("Can only connect to another TypedPort")

        # reject Generic ↔ Generic
        if self.data_type is GenericData and port.data_type is GenericData:
            return

        # allow Generic ↔ anything
        if self.data_type is GenericData or port.data_type is GenericData:
            return super().connect_to(port, push_undo, emit_signal)

        # handle ArrayData[T]
        if _array_types_compatible(self.data_type, port.data_type):
            return super().connect_to(port, push_undo, emit_signal)

        return
