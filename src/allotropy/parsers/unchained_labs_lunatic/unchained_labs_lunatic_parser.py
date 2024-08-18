from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import MapperVendorParser


class UnchainedLabsLunaticParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Unchained Labs Lunatic"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
