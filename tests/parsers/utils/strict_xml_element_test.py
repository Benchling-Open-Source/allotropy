from xml.etree.ElementTree import Element, tostring

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.values import assert_not_none


@pytest.fixture
def xml_element_bytes() -> bytes:
    return b"""
    <Root attr1="1" attr2="a">
        <Child1>abc</Child1>
        <Child2>
            <SubChild attribute="abc">123</SubChild>
        </Child2>
        <List>
            <Element>1</Element>
            <Element>2</Element>
        </List>
    </Root>
    """


@pytest.fixture
def xml_element(xml_element_bytes: bytes) -> Element:
    return fromstring(xml_element_bytes)  # type: ignore[no-any-return]


@pytest.fixture
def strict_xml_element(xml_element: Element) -> StrictXmlElement:
    return StrictXmlElement(xml_element)


def compare_xml_elements(element1: Element, element2: Element) -> bool:
    return tostring(element1) == tostring(element2)


def compare_strict_xml_elements(
    strict_element1: StrictXmlElement, strict_element2: StrictXmlElement
) -> bool:
    return compare_xml_elements(strict_element1.element, strict_element2.element)


def test_create_from_bytes(xml_element_bytes: bytes, xml_element: Element) -> None:
    assert compare_strict_xml_elements(
        StrictXmlElement(xml_element),
        StrictXmlElement.create_from_bytes(xml_element_bytes),
    )


def test_find(xml_element: Element, strict_xml_element: StrictXmlElement) -> None:
    assert compare_strict_xml_elements(
        strict_xml_element.find("Child1"),
        StrictXmlElement(assert_not_none(xml_element.find("Child1"))),
    )

    with pytest.raises(
        AllotropeConversionError, match="Unable to find missing in xml file contents"
    ):
        strict_xml_element.find("missing")


def test_recursive_find(
    xml_element: Element, strict_xml_element: StrictXmlElement
) -> None:

    assert compare_strict_xml_elements(
        strict_xml_element.recursive_find(["Child2", "SubChild"]),
        StrictXmlElement(
            assert_not_none(
                assert_not_none(xml_element.find("Child2")).find("SubChild")
            )
        ),
    )

    with pytest.raises(
        AllotropeConversionError, match="Unable to find missing in xml file contents"
    ):
        strict_xml_element.recursive_find(["Child2", "missing"])


def test_find_all(xml_element: Element, strict_xml_element: StrictXmlElement) -> None:
    strict_xml_elements = strict_xml_element.find("List").findall("Element")
    xml_elements = assert_not_none(xml_element.find("List")).findall("Element")

    for strict_element, element in zip(strict_xml_elements, xml_elements, strict=True):
        assert compare_strict_xml_elements(strict_element, StrictXmlElement(element))

    assert strict_xml_element.find("List").findall("missing") == []


def test_get_attr(strict_xml_element: StrictXmlElement) -> None:
    assert strict_xml_element.get_attr("attr1") == "1"
    assert strict_xml_element.get_attr("attr2") == "a"

    with pytest.raises(
        AllotropeConversionError, match="Unable to find missing in xml file contents"
    ):
        strict_xml_element.get_attr("missing")


def test_get_text(strict_xml_element: StrictXmlElement) -> None:
    assert strict_xml_element.find("Child1").get_text() == "abc"


def test_get_float(strict_xml_element: StrictXmlElement) -> None:
    strict_element = strict_xml_element.recursive_find(["Child2", "SubChild"])
    assert strict_element.get_float("sub child value") == 123.0

    with pytest.raises(AllotropeConversionError, match="Invalid float string: 'abc'"):
        assert strict_xml_element.find("Child1").get_float("child1 value")
