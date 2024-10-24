from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_reader import (
    ThermoFisherQubit4Reader,
)
from allotropy.parsers.thermo_fisher_qubit_flex import constants
from allotropy.parsers.thermo_fisher_qubit_flex.thermo_fisher_qubit_flex_reader import (
    ThermoFisherQubitFlexReader,
)
from allotropy.parsers.thermo_fisher_qubit_flex.thermo_fisher_qubit_flex_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherQubitFlexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = constants.DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherQubit4Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        df = ThermoFisherQubitFlexReader.read(named_file_contents)
        return create_data(df, named_file_contents.original_file_path)
