from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import create_data
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Agilent Gen5"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        data = create_data(
            SectionLinesReader(lines), named_file_contents.original_file_name
        )
        return self._get_mapper(Mapper).map_model(data)
