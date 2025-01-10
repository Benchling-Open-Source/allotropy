from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import assert_not_none

T = TypeVar("T")


@dataclass(frozen=True)
class Element:
    data: dict[str, float | str | None]

    def get_or_none(self, key: str) -> float | str | None:
        return self.data.get(key)

    def get_str_or_none(self, key: str) -> str | None:
        value = self.get_or_none(key)
        if value is None or isinstance(value, str):
            return value
        msg = f"unable to parse '{value}' as string"
        raise AllotropeConversionError(msg)

    def get_float_or_none(self, key: str) -> float | None:
        value = self.get_or_none(key)
        if value is None or isinstance(value, float):
            return value
        msg = f"unable to parse '{value}' as float"
        raise AllotropeConversionError(msg)

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
    def get_elements(cls, objects: list[T]) -> list[Element]:
        return [cls.to_element(obj) for obj in objects]
