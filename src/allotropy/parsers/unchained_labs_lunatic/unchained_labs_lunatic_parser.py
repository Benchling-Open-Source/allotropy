from __future__ import annotations

import numpy as np

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.pandas_util import read_csv
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import VendorParser


class UnchainedLabsLunaticParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Unchained Labs Lunatic"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = named_file_contents.contents
        data = read_csv(filepath_or_buffer=raw_contents).replace(np.nan, None)

        filename = named_file_contents.original_file_name
        return self._get_model(create_data(data), filename)

    def _get_model(self, data: Data, filename: str) -> Model:
        mapper = Mapper(self.get_asm_converter_name(), self._get_date_time)
        return mapper.map_model(data, filename)
