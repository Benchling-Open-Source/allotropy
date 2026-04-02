from allotropy.allotrope.models.adm.binding_affinity_analyzer.wd._2024._12.binding_affinity_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_biacore_t200_evaluation import constants
from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_data_creator import (
    create_data as _create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CytivaBiacoreT200EvaluationParser(VendorParser[Data, Model]):
    DISPLAY_NAME = constants.DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "bme"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        metadata, groups_iter = _create_data(named_file_contents)
        # Materialize iterator to list to prevent generator scope staying alive during mapping
        # TODO: True streaming would require modifying the mapper and Model serialization
        groups = list(groups_iter)
        return Data(metadata=metadata, measurement_groups=groups)
