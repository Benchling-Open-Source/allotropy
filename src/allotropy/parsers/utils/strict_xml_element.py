from __future__ import annotations

from xml.etree import ElementTree

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring

from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


class StrictXmlElement:
    @classmethod
    def create_from_bytes(cls, data: bytes) -> StrictXmlElement:
        return StrictXmlElement(fromstring(data))

    def __init__(
        self, element: ElementTree.Element, namespaces: dict[str, str] | None = None
    ):
        self.element = element
        self.namespaces = namespaces or {}

    def find_or_none(self, name: str) -> StrictXmlElement | None:
        element = self.element.find(name, self.namespaces)
        return (
            StrictXmlElement(element, self.namespaces) if element is not None else None
        )

    def find(self, name: str) -> StrictXmlElement:
        return assert_not_none(
            self.find_or_none(name),
            msg=f"Unable to find '{name}' in xml file contents",
        )

    def recursive_find_or_none(self, names: list[str]) -> StrictXmlElement | None:
        if len(names) == 0:
            return self
        name, *sub_names = names
        if element := self.find_or_none(name):
            return element.recursive_find_or_none(sub_names)
        return None

    def recursive_find(self, names: list[str]) -> StrictXmlElement:
        if len(names) == 0:
            return self
        name, *sub_names = names
        return self.find(name).recursive_find(sub_names)

    def findall(self, name: str) -> list[StrictXmlElement]:
        return [
            StrictXmlElement(element, self.namespaces)
            for element in self.element.findall(name, self.namespaces)
        ]

    def get_attr_or_none(self, name: str) -> str | None:
        value = self.element.get(name)
        return None if value is None else str(value)

    def get_attr(self, name: str) -> str:
        return assert_not_none(
            self.get_attr_or_none(name),
            msg=f"Unable to find '{name}' in xml file contents",
        )

    def parse_text_or_none(self) -> StrictXmlElement | None:
        if (text := self.get_text_or_none()) is None:
            return None
        try:
            return StrictXmlElement(fromstring(text), self.namespaces)
        except ElementTree.ParseError:
            return None

    def parse_text(self, name: str) -> StrictXmlElement:
        return assert_not_none(
            self.parse_text_or_none(),
            msg=f"Unable to parse text from xml tag '{name}' as valid xml content",
        )

    def get_text_or_none(self) -> str | None:
        return self.element.text

    def get_text(self, name: str) -> str:
        return assert_not_none(
            self.get_text_or_none(),
            msg=f"Unable to find valid string from xml tag '{name}'",
        )

    def get_float_or_none(self) -> float | None:
        return try_float_or_none(self.get_text_or_none())

    def get_float(self, name: str) -> float:
        return assert_not_none(self.get_float_or_none(), name)

    def get_sub_float_or_none(self, name: str) -> float | None:
        if element := self.find_or_none(name):
            return element.get_float_or_none()
        return None

    def get_sub_text_or_none(self, name: str) -> str | None:
        if element := self.find_or_none(name):
            return element.get_text_or_none()
        return None

    # namespace-specific methods
    def get_namespaced_attr_or_none(self, namespace_key: str, field: str) -> str | None:
        if namespace_key not in self.namespaces:
            return None
        return self.element.get(f"{{{self.namespaces.get(namespace_key)}}}{field}")

    def get_namespaced_attr(self, namespace_key: str, field: str) -> str:
        return assert_not_none(
            self.get_namespaced_attr_or_none(namespace_key, field),
            msg=f"Unable to find '{namespace_key}:{field}' in xml file contents",
        )
