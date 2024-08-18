from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Data,
    Mapper,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import create_data
from allotropy.parsers.vendor_parser import MapperVendorParser


class RocheCedexBiohtParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Roche Cedex BioHT"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
