import uuid
from typing import Self

from lightshow.document.actions.action import Action
from lightshow.document.types import Scopes


class Transaction:
    def __init__(self, id: str, global_index: int, scope: Scopes):
        self.id = id
        self.global_index = global_index
        self.scope = scope
        self.actions: list[Action] = []

    def apply(self):
        for action in self.actions:
            action.apply()

    def undo(self):
        for action in reversed(self.actions):
            action.undo()

    class TransactionBuilder:
        def __init__(self):
            self.scope = Scopes.DeviceList
            self.actions: list[Action] = []
            self.global_index = 0

        def withScope(self, scope: Scopes) -> Self:
            self.scope = scope
            return self

        def withGlobalIndex(self, global_index: int) -> Self:
            self.global_index = global_index
            return self

        def withAction(self, action_cls: type[Action], *args, **kwargs) -> Self:
            action = action_cls(
                uuid.uuid4().hex, len(self.actions), self.scope, *args, **kwargs
            )
            self.actions.append(action)
            return self

        def build(self) -> Transaction:
            trans = Transaction(uuid.uuid4().hex, self.global_index, self.scope)
            trans.actions = self.actions
            return trans
