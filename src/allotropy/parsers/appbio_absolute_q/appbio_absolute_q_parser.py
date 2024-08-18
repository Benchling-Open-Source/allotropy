from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
)
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AppbioAbsoluteQParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio AbsoluteQ"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
