from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
)
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class QiacuitydPCRParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Qiacuity dPCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
