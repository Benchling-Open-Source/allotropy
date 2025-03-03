from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field

from allotropy.calcdocs.extractor import Element
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.values import assert_not_none


@dataclass(frozen=True)
class Key:
    name: str
    value: str


@dataclass(frozen=True)
class Keys:
    entries: tuple[Key, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def add(self, name: str, value: str) -> Keys:
        return Keys(entries=(*self.entries, Key(name, value)))

    def insert(self, name: str, value: str, index: int = 0) -> Keys:
        data = list(self.entries)
        data.insert(index, Key(name, value))
        return Keys(entries=tuple(data))

    def append(self, keys: Keys) -> Keys:
        return Keys(self.entries + keys.entries)

    def get_or_none(self, name: str) -> Key | None:
        for key in self.entries:
            if key.name == name:
                return key
        return None

    def get(self, name: str) -> Key:
        return assert_not_none(
            self.get_or_none(name),
            msg=f"Unable to find key '{name}'",
        )

    def get_idx_or_none(self, name: str) -> int | None:
        for idx, key in enumerate(self.entries):
            if key.name == name:
                return idx
        return None

    def get_idx(self, name: str) -> int:
        return assert_not_none(
            self.get_idx_or_none(name),
            msg=f"Unable to find index of key '{name}'",
        )

    def overwrite(self, name: str, value: str) -> Keys:
        index = self.get_idx_or_none(name)
        if index is None:
            return self.insert(name, value, index=0)

        return Keys(
            entries=tuple(
                key if idx != index else Key(name, value)
                for idx, key in enumerate(self.entries)
            )
        )

    def delete(self, name: str) -> Keys:
        return Keys(entries=tuple(key for key in self.entries if key.name != name))

    def extract(self, name: str) -> tuple[Key, Keys]:
        return self.get(name), self.delete(name)


class ViewData:
    def __init__(
        self,
        view: View,
        name: str,
        data: dict[str, ViewData | list[Element]],
    ):
        self.view = view
        self.name = name
        self.data = data

    def filter_keys(self, keys: Keys) -> Keys:
        return self.view.filter_keys(keys)

    def iter_keys(self) -> Iterator[Keys]:
        for data_key, item in self.data.items():
            keys = Keys().add(self.name, data_key)
            if isinstance(item, ViewData):
                for sub_keys in item.iter_keys():
                    yield keys.append(sub_keys)
            else:
                yield keys

    def get_item(self, keys: Keys) -> ViewData | list[Element]:
        if keys.is_empty():
            return self

        key, new_keys = keys.extract(self.name)
        item = self.data[key.value]
        return item.get_item(new_keys) if isinstance(item, ViewData) else item

    def get_sub_view_data(self, keys: Keys) -> ViewData:
        item = self.get_item(keys)
        if isinstance(item, ViewData):
            return item
        msg = f"Unable to find sub view data with keys: {keys}."
        raise AllotropyParserError(msg)

    def get_leaf_items(self, keys: Keys) -> list[Element]:
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

    def filter_keys(self, keys: Keys) -> Keys:
        filtered_keys = self.sub_view.filter_keys(keys) if self.sub_view else Keys()
        if key := keys.get_or_none(self.name):
            return filtered_keys.overwrite(self.name, key.value)
        return filtered_keys

    def apply(self, elements: list[Element]) -> ViewData:
        return ViewData(
            view=self,
            name=self.name,
            data={
                id_: self.sub_view.apply(element) if self.sub_view else element
                for id_, element in self.sort_elements(elements).items()
            },
        )
