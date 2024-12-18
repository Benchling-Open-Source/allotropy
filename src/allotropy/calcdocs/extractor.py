from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Element:
    data: dict[str, float | str | None]

    def get(self, key: str) -> float | str | None:
        return self.data.get(key)


class Extractor(Generic[T]):
    @classmethod
    @abstractmethod
    def to_element(cls, obj: T) -> Element:
        pass

    @classmethod
    def get_elements(cls, objects: list[T]) -> list[Element]:
        return [cls.to_element(obj) for obj in objects]
