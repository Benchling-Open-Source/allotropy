from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    Data,
    Mapper,
)
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class PharmSpecParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Beckman PharmSpec"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
