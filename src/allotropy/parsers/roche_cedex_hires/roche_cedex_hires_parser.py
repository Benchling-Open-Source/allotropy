""" Parser file for Roche Cedex HiRes Instrument """
from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_structure import create_data
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexHiResParser(VendorParser):
    @property
    def display_name(self) -> str:
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)
