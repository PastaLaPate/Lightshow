import math
from typing import Type

from NodeGraphQt.base.factory import NodeFactory
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.qgraphics.node_base import NodeItem
from NodeGraphQt.qgraphics.pipe import PipeItem
from NodeGraphQt.qgraphics.port import PortItem
from NodeGraphQt.widgets.viewer import NodeViewer
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLineEdit,
    QTreeView,
    QVBoxLayout,
)

from lightshow.gui.node_editor.custom_node import CustomNode
from lightshow.gui.node_editor.datas import GenericData, NodeDataType
from lightshow.gui.node_editor.typed_port import TypedPort, TypedPortItem


class SearchLineEdit(QLineEdit):
    nav_down = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_Down:
            self.nav_down.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class SearchTree(QTreeView):
    return_key = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Return:
            self.return_key.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class CustomTabSearchTreeWidget(QDialog):
    """
    UE5-style collapsible Tab Search for nodes.
    Drop-in replacement for TabSearchMenuWidget.
    """

    search_submitted = Signal(str)

    def __init__(
        self, node_dict=None, parent=None, node_factory: NodeFactory | None = None
    ):
        super().__init__(parent)

        # ---------------- Window flags & translucent background ----------------
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # ---------------- Store node dictionary ----------------
        self._node_dict = node_dict or {}
        self._filtered_node_dict = node_dict or {}
        self._node_factory = node_factory

        # ---------------- Line edit for search ----------------
        self.line_edit = SearchLineEdit()
        self.line_edit.setPlaceholderText("Search...")
        self.line_edit.nav_down.connect(self._on_nav_down)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(self._on_return_pressed)

        # ---------------- Tree view ----------------
        self.tree = SearchTree()
        self.tree.setIndentation(12)
        self.tree.setHeaderHidden(True)
        self.model = QStandardItemModel()
        self.tree.setModel(self.model)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.clicked.connect(self._on_item_double_clicked)
        self.tree.return_key.connect(self._on_return_pressed)

        # ---------------- Layout ----------------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.tree)

        # ---------------- Internal state ----------------
        self._searched_items = []
        self.rebuild = True
        self._block_submit = False

        # ---------------- Build tree if node_dict exists ----------------
        if self._node_dict:
            self.build_tree()

    # ---------------- Public interface ----------------
    def set_nodes(self, node_dict=None):
        """Set nodes dict {name: node_type}"""
        if not self._node_dict or self.rebuild:
            self._node_dict.clear()
            self._filtered_node_dict.clear()
            self._clear_items()
            self._searched_items.clear()
            self._node_dict.update(node_dict or {})
            self._filtered_node_dict.update(node_dict or {})
            self.build_tree()
            self.rebuild = False
        self._show()

    def _show(self):
        """Show popup relative to parent window"""
        # clear search
        self.line_edit.setText("")
        self.line_edit.setFocus()
        self._block_submit = False

        # ensure widget has correct size
        self.adjustSize()

        # show first (required for popup frame geometry)
        self.show()

        # compute centered position
        fg = self.frameGeometry()
        cursor = QCursor.pos()
        pos = cursor - fg.center()

        # move to centered position
        self.move(pos)

    def _close(self):
        """Close popup"""
        self._block_submit = True
        self.hide()

    def build_tree(self):
        self.model.clear()
        root = self.model.invisibleRootItem()
        # build raw namespace tree
        tree = {}
        for display_name, full_type in self._filtered_node_dict.items():
            parts = full_type[0].split(".")
            cur = tree
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur.setdefault("_nodes", {})[display_name] = full_type

        # collapse only the root linear prefix
        def collapse_root(subtree):
            parts = []
            cur = subtree

            while True:
                keys = [k for k in cur.keys() if k != "_nodes"]
                if "_nodes" in cur or len(keys) != 1:
                    break
                key = keys[0]
                parts.append(key)
                cur = cur[key]

            return ".".join(parts), cur

        # build Qt tree
        def add_branch(parent: QStandardItem, subtree):
            # add nodes
            for name, node_type in subtree.get("_nodes", {}).items():
                item = QStandardItem(name)
                item.setData(node_type, Qt.ItemDataRole.UserRole)
                parent.appendRow(item)

            # add namespaces
            for key, val in subtree.items():
                if key == "_nodes":
                    continue
                cat = QStandardItem(key)
                cat.setSelectable(False)
                parent.appendRow(cat)
                add_branch(cat, val)

        # apply root collapsing
        for key, val in tree.items():
            prefix, subtree = collapse_root({key: val})
            label = prefix if prefix else key
            root_item = QStandardItem(label)
            root_item.setSelectable(False)
            root.appendRow(root_item)
            add_branch(root_item, subtree)

        self.tree.expandToDepth(0)

    def select_first(self):
        if not getattr(self, "_visible_indexes", None):
            return

        index = self._visible_indexes[0]

        # ensure all parents are expanded
        parent = index.parent()
        while parent.isValid():
            self.tree.expand(parent)
            parent = parent.parent()

        self.tree.setCurrentIndex(index)
        self.tree.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_nav_down(self):
        self.tree.setFocus()
        self.tree.setCurrentIndex(self.tree.indexBelow(self.tree.currentIndex()))

    # ---------------- Fuzzy search ----------------
    def _on_text_changed(self, text):
        """Filter tree based on fuzzy search"""
        matcher = text.lower()
        self._visible_indexes = []

        def apply_filter(item):
            visible = False

            for i in range(item.rowCount()):
                child = item.child(i)
                if apply_filter(child):
                    visible = True

            node_type = item.data(Qt.ItemDataRole.UserRole)
            if node_type and matcher in item.text().lower():
                visible = True
                self._visible_indexes.append(item.index())

            parent_index = item.parent().index() if item.parent() else QModelIndex()
            self.tree.setRowHidden(item.row(), parent_index, not visible)
            return visible

        root = self.model.invisibleRootItem()
        for i in range(root.rowCount()):
            apply_filter(root.child(i))

        self.tree.expandAll()
        self.select_first()

    # ---------------- Keyboard/Return ----------------
    def _on_return_pressed(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            index = self.model.index(0, 0)
        self._trigger_index(index)

    def _on_item_double_clicked(self, index):
        self._trigger_index(index)

    def _trigger_index(self, index):
        """Emit search_submitted if leaf node clicked"""
        node_type = index.data(Qt.ItemDataRole.UserRole)
        if node_type and not self._block_submit:
            self.search_submitted.emit(node_type[0])
        self._close()

    # ---------------- Helpers ----------------
    def _clear_items(self):
        self.model.clear()

    def _filter_node_dict(self, data_type: Type[NodeDataType], port_type: PortTypeEnum):
        if not self._node_factory:
            self._filtered_node_dict = self._node_dict.copy()
            return
        self._filtered_node_dict.clear()
        for display_name, full_type in self._node_dict.items():
            node = self._node_factory.create_node_instance(full_type[0])
            if not isinstance(node, CustomNode):
                self._filtered_node_dict[display_name] = full_type
                continue
            ports = (
                node.input_ports()
                if port_type == PortTypeEnum.IN
                else node.output_ports()
            )
            should_add = False
            for port in ports:
                if not isinstance(port, TypedPort):
                    continue
                if (
                    port.data_type == data_type
                    or port.data_type == GenericData
                    or data_type == GenericData
                ):
                    should_add = True
                    break
            if should_add:
                self._filtered_node_dict[display_name] = full_type

    def _clear_node_dict_filter(self):
        self._filtered_node_dict = self._node_dict.copy()


class CustomNodeViewer(NodeViewer):
    _node_factory: NodeFactory | None

    def __init__(self, parent=None, undo_stack=None):
        super().__init__(parent, undo_stack)
        self._search_widget = CustomTabSearchTreeWidget(parent=None)
        self._search_widget.search_submitted.connect(self._on_search_submitted)
        self._node_factory = None
        self._selecting_node = False

    @property
    def node_factory(self):
        return self._node_factory

    @node_factory.setter
    def node_factory(self, value: NodeFactory):
        self._node_factory = value
        self._search_widget._node_factory = value

    def establish_connection(self, start_port, end_port):
        """
        establish a new pipe connection.
        (adds a new pipe item to draw between 2 ports)
        """
        pipe = PipeItem()
        if isinstance(start_port, TypedPortItem):
            pipe._color = (
                *tuple(
                    int(start_port._data_type.color.lstrip("#")[i : i + 2], 16)
                    for i in (0, 2, 4)
                ),
                255,
            )  # Hex to rgb + 255 for alpha
            pipe.reset()
        self.scene().addItem(pipe)
        pipe.set_connections(start_port, end_port)
        pipe.draw_path(pipe.input_port, pipe.output_port)
        if start_port.node.selected or end_port.node.selected:
            pipe.highlight()
        if not start_port.node.visible or not end_port.node.visible:
            pipe.hide()

    def apply_live_connection(self, event):
        """
        triggered mouse press/release event for the scene.
        - verifies the live connection pipe.
        - makes a connection pipe if valid.
        - emits the "connection changed" signal.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent):
                The event handler from the QtWidgets.QGraphicsScene
        """
        if not self._LIVE_PIPE.isVisible() or not self._start_port:
            return

        self._start_port.hovered = False

        # find the end port.
        end_port = None
        for item in self.scene().items(event.scenePos()):
            if isinstance(item, PortItem):
                end_port = item
                break

        connected = []
        disconnected = []

        # if port disconnected from existing pipe.
        if end_port is None:
            if self._detached_port and not self._LIVE_PIPE.shift_selected:
                dist = math.hypot(
                    self._previous_pos.x() - self._origin_pos.x(),
                    self._previous_pos.y() - self._origin_pos.y(),
                )
                if dist <= 2.0:  # cursor pos threshold.
                    self.establish_connection(self._start_port, self._detached_port)
                    self._detached_port = None
                else:
                    disconnected.append((self._start_port, self._detached_port))
                    self.connection_changed.emit(disconnected, connected)

            self._detached_port = None
            # self.end_live_connection()
            if isinstance(self._start_port, TypedPortItem):
                self._search_widget._filter_node_dict(
                    self._start_port._data_type,
                    (
                        PortTypeEnum.OUT
                        if self._start_port._port_type == PortTypeEnum.IN.value
                        else PortTypeEnum.IN
                    ),
                )
                self._search_widget.build_tree()
            else:
                self._search_widget._clear_node_dict_filter()
                self._search_widget.build_tree()
            self._selecting_node = True
            self._search_widget._show()
            self.tab_search_toggle(clear=False)
            return

        else:
            if self._start_port is end_port:
                return

        # if connection to itself
        same_node_connection = end_port.node == self._start_port.node
        if not self.acyclic:
            # allow a node cycle connection.
            same_node_connection = False

        # constrain check
        accept_connection = self._validate_accept_connection(self._start_port, end_port)
        reject_connection = self._validate_reject_connection(self._start_port, end_port)

        # restore connection check.
        restore_connection = any(
            [
                # if the end port is locked.
                end_port.locked,
                # if same port type.
                end_port.port_type == self._start_port.port_type,
                # if connection to itself.
                same_node_connection,
                # if end port is the start port.
                end_port == self._start_port,
                # if detached port is the end port.
                self._detached_port == end_port,
                # if a port has a accept port type constrain.
                not accept_connection,
                # if a port has a reject port type constrain.
                reject_connection,
            ]
        )
        if restore_connection:
            if self._detached_port:
                to_port = self._detached_port or end_port
                self.establish_connection(self._start_port, to_port)
                self._detached_port = None
            self.end_live_connection()
            return

        # end connection if starting port is already connected.
        if (
            self._start_port.multi_connection
            and self._start_port in end_port.connected_ports
        ):
            self._detached_port = None
            self.end_live_connection()
            return

        # register as disconnected if not acyclic.
        if self.acyclic and not self.acyclic_check(self._start_port, end_port):
            if self._detached_port:
                disconnected.append((self._start_port, self._detached_port))

            self.connection_changed.emit(disconnected, connected)

            self._detached_port = None
            self.end_live_connection()
            return

        # make connection.
        if not end_port.multi_connection and end_port.connected_ports:
            dettached_end = end_port.connected_ports[0]
            disconnected.append((end_port, dettached_end))

        if self._detached_port:
            disconnected.append((self._start_port, self._detached_port))

        connected.append((self._start_port, end_port))

        self.connection_changed.emit(disconnected, connected)

        self._detached_port = None
        self.end_live_connection()

    def mousePressEvent(self, event):
        if self._selecting_node:
            self.end_live_connection()
        return super().mousePressEvent(event)

    def _on_search_submitted(self, node_type):
        """
        Slot function triggered when the ``TabSearchMenuWidget`` has
        submitted a search.

        This will emit the "search_triggered" signal and tell the parent node
        graph to create a new node object.

        Args:
            node_type (str): node type identifier.
        """
        pos = self.mapToScene(self._previous_pos)
        self.search_triggered.emit(node_type, (pos.x(), pos.y()))
        nodes = self.all_nodes()
        last_node = nodes[0]
        if (
            last_node.type_ == node_type
            and self._selecting_node
            and isinstance(last_node, NodeItem)
            and isinstance(self._start_port, TypedPortItem)
        ):
            self._selecting_node = False
            ports = (
                last_node.outputs
                if self._start_port._port_type == PortTypeEnum.IN.value
                else last_node.inputs
            )
            for port in ports:
                if isinstance(port, TypedPortItem):
                    if port._data_type == self._start_port._data_type:
                        self.connection_changed.emit([], [(self._start_port, port)])
                        self.end_live_connection()
                        break

    def tab_search_toggle(self, clear=True):
        state = self._search_widget.isVisible()
        if not state:
            self._search_widget.setVisible(state)
            self.setFocus()
            return
        if clear:
            self._search_widget._clear_node_dict_filter()
            self._search_widget.build_tree()
        cursor = QCursor.pos()
        self._search_widget.adjustSize()
        self._search_widget.show()
        self._search_widget.move(cursor)
        self._search_widget.build_tree()
        cursor = QCursor.pos()
        self._search_widget.adjustSize()
        self._search_widget.show()
        self._search_widget.move(cursor)
