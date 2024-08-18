from __future__ import annotations

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Mapper,
)
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class ViCellBluParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Beckman Vi-Cell BLU"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
