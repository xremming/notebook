import abc
from typing import Generic, TypeVar

T = TypeVar("T")


class Storage(Generic[T], abc.ABC):
    @abc.abstractmethod
    def __getitem__(self, index: int) -> T | None:
        ...

    @abc.abstractmethod
    def __setitem__(self, index: int, value: T) -> None:
        ...

    @abc.abstractmethod
    def __delitem__(self, index: int) -> None:
        ...


class ListStorage(Storage[T]):
    def __init__(self) -> None:
        self._items: list[T | None] = []

    def __getitem__(self, index: int) -> T | None:
        if index < 0 or index >= len(self._items):
            return None
        return self._items[index]

    def __setitem__(self, index: int, value: T) -> None:
        if index < 0:
            raise IndexError(f"Index must not be negative: {index}")

        if index >= len(self._items):
            self._items.extend([None] * (index - len(self._items) + 1))

        if value is None:
            raise ValueError("Value must not be None")

        self._items[index] = value

    def __delitem__(self, index: int) -> None:
        if index < 0:
            raise IndexError(f"Index must not be negative: {index}")

        if index >= len(self._items):
            return

        self._items[index] = None


class DictStorage(Storage[T]):
    def __init__(self) -> None:
        self._items: dict[int, T | None] = {}

    def __getitem__(self, index: int) -> T | None:
        return self._items.get(index, None)

    def __setitem__(self, index: int, value: T) -> None:
        if index < 0:
            raise IndexError(f"Index must not be negative: {index}")

        if value is None:
            raise ValueError("Value must not be None")

        self._items[index] = value

    def __delitem__(self, index: int) -> None:
        if index in self._items:
            del self._items[index]


if __name__ == "__main__":
    from itertools import zip_longest

    a = ListStorage[int]()
    a[1] = 1

    b = ListStorage[int]()
    b[2] = 2

    c = ListStorage[int]()
    c[3] = 3

    for x, y, z in zip_longest(a._items, b._items, c._items):
        print(x, y, z)
