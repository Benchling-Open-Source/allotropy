from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import Mapper
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_reader import QiacuitydPCRReader
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class QiacuitydPCRParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Qiacuity dPCR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        reader = QiacuitydPCRReader(named_file_contents.contents)
        data = create_data(reader.well_data, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
