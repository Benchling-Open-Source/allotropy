from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Data as MapperData,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_biacore_insight.constants import DISPLAY_NAME
from allotropy.parsers.cytiva_biacore_insight.cytiva_biacore_insight_reader import (
    CytivaBiacoreInsightReader,
)
from allotropy.parsers.cytiva_biacore_insight.cytiva_biacore_insight_structure import (
    create_measurement_groups,
    create_metadata,
    Data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CytivaBiacoreInsightParser(VendorParser[MapperData, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = CytivaBiacoreInsightReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> MapperData:
        reader = CytivaBiacoreInsightReader.create(named_file_contents)
        data = Data.create(reader)
        return MapperData(
            create_metadata(data.metadata, named_file_contents.original_file_path),
            create_measurement_groups(data),
        )
