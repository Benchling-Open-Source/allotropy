from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class NovaBioFlexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "NovaBio Flex2"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_mapper(Mapper).map_model(create_data(named_file_contents))
