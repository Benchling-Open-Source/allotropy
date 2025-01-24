from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from allotropy.calcdocs.extractor import Element
from allotropy.exceptions import AllotropyParserError


def head_tail_dict(
    data: dict[str, str], key: str
) -> tuple[dict[str, str], dict[str, str]]:
    new_keys = data.copy()
    return {key: new_keys.pop(key)}, new_keys


class ViewData:
    def __init__(self, name: str, data: dict[str, ViewData | list[Element]]):
        self.name = name
        self.data = data

    def iter_names(self) -> Iterator[str]:
        yield self.name
        for item in self.data.values():
            if isinstance(item, ViewData):
                yield from item.iter_names()
            break

    def iter_keys(self) -> Iterator[dict[str, str]]:
        for key, item in self.data.items():
            full_key = {self.name: key}
            if isinstance(item, ViewData):
                for sub_keys in item.iter_keys():
                    yield {
                        **full_key,
                        **sub_keys,
                    }
            else:
                yield full_key

    def filter_keys(self, keys: dict[str, str]) -> dict[str, str]:
        return {
            name: key_value
            for name in self.iter_names()
            if (key_value := keys.get(name)) is not None
        }

    def get_item(self, keys: dict[str, str]) -> ViewData | list[Element]:
        if not keys:
            return self

        head, tail = head_tail_dict(keys, self.name)
        item = self.data[head[self.name]]
        return item.get_item(tail) if isinstance(item, ViewData) else item

    def get_sub_view_data(self, keys: dict[str, str]) -> ViewData:
        item = self.get_item(keys)
        if isinstance(item, ViewData):
            return item
        msg = f"Unable to find sub view data with keys: {keys}."
        raise AllotropyParserError(msg)

    def get_leaf_items(self, keys: dict[str, str]) -> list[Element]:
        item = self.get_item(keys)
        if isinstance(item, ViewData):
            msg = f"Unable to find leaf item of view data with keys: {keys}."
            raise AllotropyParserError(msg)
        return item


class View(ABC):
    def __init__(self, name: str, sub_view: View | None = None):
        self.name = name
        self.sub_view = sub_view

    @abstractmethod
    def sort_elements(self, _: list[Element]) -> dict[str, list[Element]]:
        pass

    def apply(self, elements: list[Element]) -> ViewData:
        return ViewData(
            name=self.name,
            data={
                id_: self.sub_view.apply(element) if self.sub_view else element
                for id_, element in self.sort_elements(elements).items()
            },
        )
