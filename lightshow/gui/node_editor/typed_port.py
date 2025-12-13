from typing import Type, TypeVar

from NodeGraphQt import Port
from NodeGraphQt.qgraphics.port import PortEnum, PortItem
from PySide6 import QtCore, QtGui

from lightshow.gui.node_editor.datas import NodeDataType

T = TypeVar("T")


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
        self.data_type = data_type

    def connect_to(self, port=None, push_undo=True, emit_signal=True):
        if not isinstance(port, TypedPort):
            raise TypeError("Can only connect to another TypedPort")
        if self.data_type != port.data_type:
            return
        return super().connect_to(port, push_undo, emit_signal)
