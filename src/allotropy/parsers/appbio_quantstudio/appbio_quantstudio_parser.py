from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AppBioQuantStudioParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio QuantStudio RT-PCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
