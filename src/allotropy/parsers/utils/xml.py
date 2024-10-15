from xml.etree.ElementTree import Element

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_nan,
    try_float_or_none,
)


def get_element_from_xml(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> Element:
    if tag_name_2 is not None:
        tag_finder = tag_name + "/" + tag_name_2
        xml_element = xml_object.find(tag_finder)
    else:
        tag_finder = tag_name
        xml_element = xml_object.find(tag_finder)
    if xml_element is not None:
        return xml_element
    else:
        msg = f"Unable to find '{tag_finder}' from xml."
        raise AllotropeConversionError(msg)


def get_val_from_xml(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> str:
    return str(get_element_from_xml(xml_object, tag_name, tag_name_2).text)


def get_val_from_xml_or_none(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> str | None:
    try:
        val_from_xml = get_element_from_xml(xml_object, tag_name, tag_name_2).text
        if val_from_xml is not None:
            return str(val_from_xml)
        else:
            return None
    except AllotropeConversionError:
        return None


def get_float_from_xml_or_nan(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> JsonFloat:
    return try_float_or_nan(get_val_from_xml_or_none(xml_object, tag_name, tag_name_2))


def get_float_from_xml_or_none(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> float | None:
    return try_float_or_none(get_val_from_xml_or_none(xml_object, tag_name, tag_name_2))


def get_float_from_xml(
    xml_object: Element, tag_name: str, tag_name_2: str | None = None
) -> float:
    return assert_not_none(get_float_from_xml_or_none(xml_object, tag_name, tag_name_2))


def get_attrib_from_xml(
    xml_object: Element,
    tag_name: str,
    attrib_name: str,
    tag_name_2: str | None = None,
) -> str:
    xml_element = get_element_from_xml(xml_object, tag_name, tag_name_2)
    try:
        attribute_val = xml_element.attrib[attrib_name]
        return attribute_val
    except KeyError as e:
        msg = f"Unable to find '{attrib_name}' in {xml_element.attrib}"
        raise AllotropeConversionError(msg) from e


def get_children_with_tag(xml_object: Element, tag: str) -> list[Element]:
    return [child for child in xml_object if child.tag == tag]
