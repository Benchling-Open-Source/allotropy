from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    Data,
    Mapper,
)
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AgilentTapestationAnalysisParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent TapeStation Analysis"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    CREATE_DATA = staticmethod(create_data)
