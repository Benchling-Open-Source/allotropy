from xml.etree.ElementTree import Element, tostring

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring
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
        <Child3></Child3>
        <List>
            <Element>1</Element>
            <Element>2</Element>
        </List>
    </Root>
    """


@pytest.fixture
def xml_element(xml_element_bytes: bytes) -> Element:
    return fromstring(xml_element_bytes)


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


def test_find_or_none(
    xml_element: Element, strict_xml_element: StrictXmlElement
) -> None:
    child1 = strict_xml_element.find_or_none("Child1")

    assert child1 is not None
    assert compare_strict_xml_elements(
        child1,
        StrictXmlElement(assert_not_none(xml_element.find("Child1"))),
    )

    assert strict_xml_element.find_or_none("missing") is None


def test_find(xml_element: Element, strict_xml_element: StrictXmlElement) -> None:
    assert compare_strict_xml_elements(
        strict_xml_element.find("Child1"),
        StrictXmlElement(assert_not_none(xml_element.find("Child1"))),
    )

    with pytest.raises(
        AllotropeConversionError, match="Unable to find 'missing' in xml file contents"
    ):
        strict_xml_element.find("missing")


def test_recursive_find_or_none(
    xml_element: Element, strict_xml_element: StrictXmlElement
) -> None:
    sub_child = strict_xml_element.recursive_find_or_none(["Child2", "SubChild"])

    assert sub_child is not None
    assert compare_strict_xml_elements(
        sub_child,
        StrictXmlElement(
            assert_not_none(
                assert_not_none(xml_element.find("Child2")).find("SubChild")
            )
        ),
    )

    assert strict_xml_element.recursive_find_or_none(["Child2", "missing"]) is None


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
        AllotropeConversionError, match="Unable to find 'missing' in xml file contents"
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
        AllotropeConversionError, match="Unable to find 'missing' in xml file contents"
    ):
        strict_xml_element.get_attr("missing")


def test_get_text_or_none(strict_xml_element: StrictXmlElement) -> None:
    assert strict_xml_element.find("Child1").get_text_or_none() == "abc"
    assert strict_xml_element.find("Child3").get_text_or_none() is None


def test_get_text(strict_xml_element: StrictXmlElement) -> None:
    assert strict_xml_element.find("Child1").get_text("Child1") == "abc"

    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find valid string from xml tag 'Child3'",
    ):
        assert strict_xml_element.find("Child3").get_text("Child3")


def test_get_float_or_none(strict_xml_element: StrictXmlElement) -> None:
    strict_element = strict_xml_element.recursive_find(["Child2", "SubChild"])
    assert strict_element.get_float_or_none() == 123.0

    assert strict_xml_element.find("Child1").get_float_or_none() is None


def test_get_float(strict_xml_element: StrictXmlElement) -> None:
    strict_element = strict_xml_element.recursive_find(["Child2", "SubChild"])
    assert strict_element.get_float("sub child value") == 123.0

    with pytest.raises(
        AllotropeConversionError, match="Expected non-null value for child1 value"
    ):
        assert strict_xml_element.find("Child1").get_float("child1 value")


def test_get_sub_float_or_none(strict_xml_element: StrictXmlElement) -> None:
    strict_element = strict_xml_element.find("Child2")
    assert strict_element.get_sub_float_or_none("SubChild") == 123.0

    assert strict_element.get_sub_float_or_none("missing") is None


def test_get_sub_text_or_none(strict_xml_element: StrictXmlElement) -> None:
    assert strict_xml_element.get_sub_text_or_none("Child1") == "abc"

    assert strict_xml_element.get_sub_text_or_none("missing") is None


@pytest.fixture
def xml_element_with_namespaces_bytes() -> bytes:
    return b"""
    <Root xmlns:ns1="http://example.com/ns1" xmlns:ns2="http://example.com/ns2">
        <Element ns1:attr1="value1" ns2:attr2="value2" attr3="value3"/>
        <ns1:Element>ns1 element content</ns1:Element>
        <ns2:Element>ns2 element content</ns2:Element>
    </Root>
    """


@pytest.fixture
def xml_element_with_namespaces(xml_element_with_namespaces_bytes: bytes) -> Element:
    return fromstring(xml_element_with_namespaces_bytes)


@pytest.fixture
def strict_xml_element_with_namespaces(
    xml_element_with_namespaces: Element,
) -> StrictXmlElement:
    namespaces = {"ns1": "http://example.com/ns1", "ns2": "http://example.com/ns2"}
    return StrictXmlElement(xml_element_with_namespaces, namespaces)


def test_get_namespaced_attr_or_none(
    strict_xml_element_with_namespaces: StrictXmlElement,
) -> None:
    element = strict_xml_element_with_namespaces.find("Element")

    assert element.get_namespaced_attr_or_none("ns1", "attr1") == "value1"
    assert element.get_namespaced_attr_or_none("ns2", "attr2") == "value2"

    assert element.get_namespaced_attr_or_none("ns1", "missing") is None

    assert element.get_namespaced_attr_or_none("missing_ns", "attr1") is None


def test_get_namespaced_attr(
    strict_xml_element_with_namespaces: StrictXmlElement,
) -> None:
    element = strict_xml_element_with_namespaces.find("Element")

    assert element.get_namespaced_attr("ns1", "attr1") == "value1"
    assert element.get_namespaced_attr("ns2", "attr2") == "value2"

    # Test getting non-existent attribute raises exception
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find 'ns1:missing' in xml file contents",
    ):
        element.get_namespaced_attr("ns1", "missing")

    # Test getting attribute with non-existent namespace raises exception
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find 'missing_ns:attr1' in xml file contents",
    ):
        element.get_namespaced_attr("missing_ns", "attr1")


def test_find_with_namespaces(
    strict_xml_element_with_namespaces: StrictXmlElement,
) -> None:
    ns1_element = strict_xml_element_with_namespaces.find("ns1:Element")
    assert ns1_element.get_text_or_none() == "ns1 element content"

    ns2_element = strict_xml_element_with_namespaces.find("ns2:Element")
    assert ns2_element.get_text_or_none() == "ns2 element content"
