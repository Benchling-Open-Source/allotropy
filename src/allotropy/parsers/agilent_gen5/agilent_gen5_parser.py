from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AgilentGen5Parser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
