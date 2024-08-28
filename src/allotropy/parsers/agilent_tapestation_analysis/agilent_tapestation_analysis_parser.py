from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AgilentTapestationAnalysisParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent TapeStation Analysis"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "xml"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        try:
            root_element = ET.parse(  # noqa: S314
                named_file_contents.contents
            ).getroot()
        except ET.ParseError as e:
            msg = f"There was an error when trying to read the xml file: {e}"
            raise AllotropeParsingError(msg) from e

        measurement_groups, calculated_data = create_measurement_groups(root_element)
        return Data(
            create_metadata(root_element, named_file_contents.original_file_name),
            measurement_groups,
            # NOTE: in current implementation, calculated data is reported at global level for some reason.
            # TODO(nstender): should we move this inside of measurements?
            calculated_data,
        )
