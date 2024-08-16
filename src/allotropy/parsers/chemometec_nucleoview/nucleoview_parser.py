from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.nucleoview_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class ChemometecNucleoviewParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "ChemoMetec Nucleoview"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._get_mapper(Mapper).map_model(data)
