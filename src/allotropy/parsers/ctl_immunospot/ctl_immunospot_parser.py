from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.ctl_immunospot.ctl_immunospot_structure import create_data
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "CTL ImmunoSpot"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        data = create_data(LinesReader(lines))
        return self._get_mapper(Mapper).map_model(data)
