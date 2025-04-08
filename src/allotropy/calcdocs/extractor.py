from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from allotropy.parsers.utils.calculated_data_documents.definition import Referenceable
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none

T = TypeVar("T")


@dataclass
class Element(Referenceable):
    data: dict[str, float | str | None]

    def get_or_none(self, key: str) -> float | str | None:
        return self.data.get(key)

    def get_str_or_none(self, key: str) -> str | None:
        value = self.get_or_none(key)
        return value if value is None else str(value)

    def get_float_or_none(self, key: str) -> float | None:
        value = self.get_or_none(key)
        return try_float_or_none(value)

    def get_str(self, key: str) -> str:
        return assert_not_none(self.get_str_or_none(key), key)

    def get_float(self, key: str) -> float:
        return assert_not_none(self.get_float_or_none(key), key)


class Extractor(Generic[T]):
    @classmethod
    @abstractmethod
    def to_element(cls, obj: T) -> Element:
        pass

    @classmethod
    def to_element_with_extra_data(
        cls, obj: T, extra_data: dict[str, float | str | None]
    ) -> Element:
        element = cls.to_element(obj)
        element.data |= extra_data
        return element

    @classmethod
    def get_elements(cls, objects: list[T]) -> list[Element]:
        return [cls.to_element(obj) for obj in objects]
