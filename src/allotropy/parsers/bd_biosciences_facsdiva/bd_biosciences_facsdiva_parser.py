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
from allotropy.parsers.bd_biosciences_facsdiva.bd_biosciences_facsdiva_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.bd_biosciences_facsdiva.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.vendor_parser import VendorParser


class BDFACSDivaParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "xml"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        try:
            root_element_et = ET.parse(  # noqa: S314
                named_file_contents.contents
            ).getroot()
            root_element = StrictXmlElement(root_element_et)
        except ET.ParseError as e:
            msg = f"There was an error when trying to read the xml file: {e}"
            raise AllotropeParsingError(msg) from e

        return Data(
            metadata=create_metadata(
                root_element, named_file_contents.original_file_path
            ),
            measurement_groups=create_measurement_groups(root_element),
        )
