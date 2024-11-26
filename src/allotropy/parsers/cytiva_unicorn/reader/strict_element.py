from __future__ import annotations

from xml.etree import ElementTree

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

from allotropy.parsers.utils.values import assert_not_none, try_float


class StrictElement:
    @classmethod
    def create_from_bytes(cls, data: bytes) -> StrictElement:
        return StrictElement(fromstring(data))

    def __init__(self, element: ElementTree.Element):
        self.element = element

    def find(self, name: str) -> StrictElement:
        return StrictElement(
            assert_not_none(
                self.element.find(name),
                msg=f"Unable to find {name} in xml file contents",
            )
        )

    def recursive_find(self, names: list[str]) -> StrictElement:
        if len(names) == 0:
            return self
        name, *sub_names = names
        return self.find(name).recursive_find(sub_names)

    def findall(self, name: str) -> list[StrictElement]:
        return [StrictElement(element) for element in self.element.findall(name)]

    def get_attr(self, name: str) -> str:
        return str(
            assert_not_none(
                self.element.get(name),
                msg=f"Unable to find {name} in xml file contents",
            )
        )

    def get_text(self) -> str:
        return str(self.element.text)

    def get_float(self, name: str) -> float:
        return try_float(self.get_text(), name)
