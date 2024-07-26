from __future__ import annotations

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import create_reader_data
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class ViCellXRParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman Vi-Cell XR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        reader = create_reader_data(named_file_contents)
        data = create_data(reader, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
