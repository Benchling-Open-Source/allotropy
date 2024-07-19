from __future__ import annotations

import numpy as np

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.pandas_util import read_csv
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
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
        contents = read_csv(filepath_or_buffer=raw_contents).replace(np.nan, None)
        data = create_data(contents, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
