from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.pandas_util import read_csv
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import Mapper
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio AbsoluteQ"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data_frame = read_csv(named_file_contents.contents, parse_dates=["Date"])
        data = create_data(data_frame, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
