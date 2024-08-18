from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import MapperVendorParser


class NanodropEightParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Thermo Fisher NanoDrop Eight"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
