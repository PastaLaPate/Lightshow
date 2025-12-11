from NodeGraphQt.widgets.tab_search import TabSearchMenuWidget
from NodeGraphQt.widgets.viewer import NodeViewer
from Qt import QtWidgets


class CustomTabSearchMenuWidget(TabSearchMenuWidget):
    def build_menu_tree(self):
        """
        Build hierarchical menu for nodes.
        Collapses single-child namespaces and avoids duplicate actions.
        """
        # Step 1: Build tree
        tree = {}
        for node_name, node_type in self._node_dict.items():
            parts = node_type.split(".")
            current = tree

            # all but last part are namespaces
            for part in parts[:-1]:
                current = current.setdefault(part, {})

            # last part is NOT a namespace — attach node here
            current.setdefault("_nodes", []).append(node_name)
        self._menus = {}
        self._actions = {}

        # Step 2: Recursive function to build menus
        def add_subtree(parent_menu, subtree, path=""):
            # Collapse single-child chains
            while True:
                keys = [k for k in subtree.keys() if k != "_nodes"]

                # stop if no more sub-namespaces or if this is a leaf (only _nodes)
                if len(keys) != 1:
                    break

                single_key = keys[0]
                child = subtree[single_key]

                # If the child only contains _nodes → it's a LEAF, do NOT make it a menu
                if set(child.keys()) == {"_nodes"}:
                    break

                # otherwise it's a real namespace → collapse
                path = f"{path}.{single_key}" if path else single_key
                subtree = child

            # create menu for current level if parent_menu exists
            if path:
                menu_name = path.split(".")[-1]
                menu = QtWidgets.QMenu(menu_name, self)
                menu.setStyleSheet(self._menu_stylesheet)
                if parent_menu:
                    parent_menu.addMenu(menu)
                else:
                    self.addMenu(menu)
                self._menus[path] = menu
            else:
                menu = parent_menu

            # add leaf nodes as actions
            for display_name in subtree.get("_nodes", []):
                if display_name in self._actions:
                    continue  # avoid duplicates
                action = QtWidgets.QAction(display_name, self)
                action.triggered.connect(self._on_search_submitted)
                self._actions[display_name] = action
                target_menu = menu if menu else self
                target_menu.addAction(action)

            # recurse into remaining submenus
            for k, v in subtree.items():
                if k == "_nodes":
                    continue
                add_subtree(menu, v, path=f"{path}.{k}" if path else k)

        add_subtree(None, tree)


class CustomNodeViewer(NodeViewer):
    def __init__(self, parent=None, undo_stack=None):
        super().__init__(parent, undo_stack)
        self._search_widget = CustomTabSearchMenuWidget()
        self._search_widget.search_submitted.connect(self._on_search_submitted)
