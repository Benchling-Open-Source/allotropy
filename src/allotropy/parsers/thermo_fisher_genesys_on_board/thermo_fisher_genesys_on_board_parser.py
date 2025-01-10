from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_genesys_on_board.constants import (
    DISPLAY_NAME,
    SOFTWARE_NAME,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_reader import (
    ThermoFisherVisionliteReader,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_structure import (
    VisionLiteData,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherGenesysOnBoardParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherVisionliteReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        return VisionLiteData.create(
            ThermoFisherVisionliteReader(named_file_contents),
            named_file_contents.original_file_path,
            software_name=SOFTWARE_NAME,
        )
