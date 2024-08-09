""" Parser file for ThermoFisher Qubit 4 Adapter """

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit4 import constants
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_reader import (
    ThermoFisherQubit4Reader,
)
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherQubit4Parser(VendorParser):
    """
    Parser for the ThermoFisher Qubit 4 data files.

    This parser reads data from ThermoFisher Qubit 4 files and converts it into an Allotrope model. The main functionalities
    include extracting and converting specific measurement and device control data, as well as handling custom sample and
    device information.
    """

    @property
    def display_name(self) -> str:
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        df = ThermoFisherQubit4Reader.read(named_file_contents)
        data = create_data(df, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
