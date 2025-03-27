from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Data as MapperData,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_data_creator import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_decoder import (
    decode_data,
)
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_structure import (
    Data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CytivaBiacoreT200ControlParser(VendorParser[MapperData, Model]):
    DISPLAY_NAME = constants.DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "blr"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> MapperData:
        data = Data.create(decode_data(named_file_contents))
        return MapperData(
            metadata=create_metadata(data, named_file_contents),
            measurement_groups=create_measurement_groups(data),
            calculated_data=create_calculated_data(data),
        )
