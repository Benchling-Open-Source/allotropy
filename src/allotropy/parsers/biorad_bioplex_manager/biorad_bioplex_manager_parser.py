from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BioradBioplexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Bio-Rad Bio-Plex Manager"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)
