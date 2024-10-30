from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_genesys30.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_reader import (
    ThermoFisherGenesys30Reader,
)
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherGenesys30Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherGenesys30Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = ThermoFisherGenesys30Reader(named_file_contents)
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(reader.header, reader.data),
        )
