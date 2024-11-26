from __future__ import annotations

from xml.etree import ElementTree

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

from allotropy.parsers.utils.values import assert_not_none


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

    def findall(self, name: str) -> list[StrictElement]:
        return [StrictElement(element) for element in self.element.findall(name)]

    def get(self, name: str) -> str:
        return assert_not_none(
            self.element.get(name),
            msg=f"Unable to find {name} in xml file contents",
        )

    def recursive_find(self, names: list[str]) -> StrictElement:
        if len(names) == 0:
            return self
        name, *sub_names = names
        return self.find(name).recursive_find(sub_names)

    def find_attr(self, names: list[str], attr: str) -> str:
        return self.recursive_find(names).get(attr)

    def find_text(self, names: list[str]) -> str:
        return str(self.recursive_find(names).element.text)
