from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from allotropy.calcdocs.extractor import Element
from allotropy.exceptions import AllotropyParserError


class ViewData:
    def __init__(self, data: dict[str, ViewData | list[Element]]):
        self.data = data

    def iter_keys(self) -> Iterator[list[str]]:
        for key, item in self.data.items():
            if isinstance(item, ViewData):
                for sub_keys in item.iter_keys():
                    yield [key, *sub_keys]
            else:
                yield [key]

    def get_item(self, *keys: str) -> ViewData | list[Element]:
        if len(keys) == 0:
            return self

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
        msg = f"Unable to find sub view data with keys: {keys}."
        raise AllotropyParserError(msg)

    def get_leaf_item(self, *keys: str) -> list[Element]:
        item = self.get_item(*keys)
        if isinstance(item, ViewData):
            msg = f"Unable to find leaf item of view data with keys: {keys}."
            raise AllotropyParserError(msg)
        return item


class View(ABC):
    def __init__(self, sub_view: View | None = None):
        self.sub_view = sub_view

    @abstractmethod
    def sort_elements(self, _: list[Element]) -> dict[str, list[Element]]:
        pass

    def apply(self, elements: list[Element]) -> ViewData:
        return ViewData(
            {
                id_: self.sub_view.apply(element) if self.sub_view else element
                for id_, element in self.sort_elements(elements).items()
            }
        )
