from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import create_data
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexBiohtParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Roche Cedex BioHT"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)
