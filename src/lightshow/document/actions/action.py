from abc import ABC, abstractmethod


class Action(ABC):
    def __init__(self, id: str, index: int, *args, **kwargs):
        super().__init__()
        self.id = id
        self.index = index

    @abstractmethod
    def apply(self):
        pass

    @abstractmethod
    def undo(self):
        pass
