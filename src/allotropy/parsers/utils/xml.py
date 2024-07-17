from xml.etree import ElementTree

from allotropy.exceptions import AllotropeConversionError


def get_element_from_xml(
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> ElementTree.Element:
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
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> str:
    return str(get_element_from_xml(xml_object, tag_name, tag_name_2).text)


def get_val_from_xml_or_none(
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> str | None:
    try:
        val_from_xml = get_element_from_xml(xml_object, tag_name, tag_name_2).text
        if val_from_xml is not None:
            return str(val_from_xml)
        else:
            return None
    except AllotropeConversionError:
        return None


def get_attrib_from_xml(
    xml_object: ElementTree.Element,
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
