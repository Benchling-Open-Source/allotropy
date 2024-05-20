from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar

from allotropy.exceptions import AllotropeConversionError

T = TypeVar("T")


class ViewData(Generic[T]):
    def __init__(self, data: dict[str, ViewData[T] | list[T]]):
        self.data = data

    def get_first_key(self) -> str:
        key, *_ = self.data.keys()
        return key

    def iter_keys(self) -> Iterator[list[str]]:
        for key, item in self.data.items():
            if isinstance(item, ViewData):
                for sub_keys in item.iter_keys():
                    yield [key, *sub_keys]
            else:
                yield [key]

    def get_item(self, *keys: str) -> ViewData[T] | list[T]:
        if len(keys) == 0:
            return self.data[self.get_first_key()]

        key, *sub_keys = keys
        item = self.data[key]
        if isinstance(item, ViewData):
            return item.get_item(*sub_keys)
        else:
            return item

    def get_sub_view_data(self, *keys: str) -> ViewData[T]:
        item = self.get_item(*keys)
        if isinstance(item, ViewData):
            return item
        msg = f"Unable to find sub view data with keys: {keys}."
        raise AllotropeConversionError(msg)

    def get_leaf_item(self, *keys: str) -> list[T]:
        item = self.get_item(*keys)
        if isinstance(item, ViewData):
            msg = f"Unable to find leaf item of view data with keys: {keys}."
            raise AllotropeConversionError(msg)
        return item


class View(ABC, Generic[T]):
    def __init__(self, sub_view: View[T] | None = None):
        self.sub_view = sub_view

    @abstractmethod
    def sort_elements(self, _: list[T]) -> dict[str, list[T]]:
        pass

    def apply(self, elements: list[T]) -> ViewData[T]:
        return ViewData(
            {
                id_: self.sub_view.apply(element) if self.sub_view else element
                for id_, element in self.sort_elements(elements).items()
            }
        )
