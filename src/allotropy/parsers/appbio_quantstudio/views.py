from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, Optional, TypeVar, Union

from allotropy.allotrope.allotrope import AllotropeConversionError

T = TypeVar("T")


class ViewData(Generic[T]):
    def __init__(self, data: dict[str, Union[ViewData, list[T]]]):
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

    def get_item(self, *keys: str) -> Union[ViewData, list[T]]:
        if len(keys) == 0:
            return self.data[self.get_first_key()]

        key, *sub_keys = keys
        item = self.data[key]
        if isinstance(item, ViewData):
            return item.get_item(*sub_keys)
        else:
            return item

    def get_sub_view_data(self, *keys: str) -> ViewData:
        item = self.get_item(*keys)
        if isinstance(item, ViewData):
            return item
        msg = f"Unable to get sub view data with keys {keys}"
        raise AllotropeConversionError(msg)

    def get_leaf_item(self, *keys: str) -> list[T]:
        item = self.get_item(*keys)
        if isinstance(item, ViewData):
            msg = f"Unable to get leaf item of view data with keys {keys}"
            raise AllotropeConversionError(msg)
        return item


class View(Generic[T]):
    def __init__(self, sub_view: Optional[View] = None):
        self.sub_view = sub_view

    def sort_elements(self, _: list[T]) -> dict[str, list[T]]:
        return {}

    def apply(self, elements: list[T]) -> ViewData:
        return ViewData(
            {
                id_: self.sub_view.apply(element) if self.sub_view else element
                for id_, element in self.sort_elements(elements).items()
            }
        )
