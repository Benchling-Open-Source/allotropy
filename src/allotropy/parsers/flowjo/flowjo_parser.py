import re
import xml.etree.ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.adm.flow_cytometry.benchling._2025._03.flow_cytometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.flow_cytometry.benchling._2025._03.flow_cytometry import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.flowjo.constants import DISPLAY_NAME
from allotropy.parsers.flowjo.flowjo_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.vendor_parser import VendorParser


def extract_flowjo_namespaces(root_element: ET.Element) -> dict[str, str]:
    attributes = root_element.attrib.items()
    namespaces_text = next(
        (value for key, value in attributes if re.search(r"{.*}", key) is not None),
        None,
    )
    if namespaces_text is None:
        return {}

    namespace_list = namespaces_text.split()
    namespaces = {
        "transforms": next(
            (ns for ns in namespace_list if "transformations" in ns), ""
        ),
        "data-type": next((ns for ns in namespace_list if "datatypes" in ns), ""),
        "gating": next((ns for ns in namespace_list if "gating" in ns), ""),
    }

    # Extract all xmlns namespace declarations
    for key, value in attributes:
        if key.startswith("xmlns:"):
            prefix = key[6:]  # Remove "xmlns:" prefix
            if prefix not in namespaces:  # Don't override existing mappings
                namespaces[prefix] = value

    # ElementTree doesn't preserve xmlns declarations as attributes, but we can detect namespace usage
    # and add common mappings manually
    for key, _ in attributes:
        if key.startswith("{http://www.w3.org/2001/XMLSchema-instance}"):
            namespaces["xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
            break

    return namespaces


class FlowjoParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "wsp"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        try:
            root_element_et = ET.parse(  # noqa: S314
                named_file_contents.contents
            ).getroot()
            # Extract namespaces and create StrictXmlElement
            namespaces = extract_flowjo_namespaces(root_element_et)
            root_element = StrictXmlElement(root_element_et, namespaces)
        except ET.ParseError as e:
            msg = f"There was an error when trying to read the xml file: {e}"
            raise AllotropeParsingError(msg) from e

        return Data(
            metadata=create_metadata(
                root_element, named_file_contents.original_file_path
            ),
            measurement_groups=create_measurement_groups(root_element),
        )
