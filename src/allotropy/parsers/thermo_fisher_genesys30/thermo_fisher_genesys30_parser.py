""" Parser file for ThermoFisher Genesys 30 Adapter """

from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_genesys30.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherGenesys30Parser(VendorParser):
    """
    Parser for the ThermoFisher Genesys 30 spectrophotometer data files.

    This parser reads data from ThermoFisher Genesys 30 spectrophotometer instrument files and converts it into an Allotrope model. The main functionalities
    include extracting and converting specific measurement and device control data, as well as handling custom sample and
    device information.
    """

    @property
    def display_name(self) -> str:
        return DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.WORKING_DRAFT

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        """
        Converts the given named file contents to an Allotrope model.

        :param named_file_contents: The contents of the file to convert.
        :return: The converted Allotrope model.
        """
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)
