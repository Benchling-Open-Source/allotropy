from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.luminex_intelliflex.constants import DISPLAY_NAME
from allotropy.parsers.luminex_intelliflex.luminex_intelliflex_reader import (
    LuminexIntelliflexReader,
)
from allotropy.parsers.luminex_intelliflex.luminex_intelliflex_structure import (
    create_data_from_reader,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class LuminexIntelliflexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = LuminexIntelliflexReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = LuminexIntelliflexReader.read(named_file_contents)
        data = create_data_from_reader(reader)
        return Data(
            create_metadata(
                data.header, data.calibrations, named_file_contents.original_file_path
            ),
            *create_measurement_groups(data.measurement_list.measurements, data.header),
        )
