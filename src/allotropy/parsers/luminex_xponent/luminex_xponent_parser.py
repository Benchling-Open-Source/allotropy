from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Data as MapperData,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    create_measurement_groups,
    create_metadata,
    Data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class LuminexXponentParser(VendorParser[MapperData, Model]):
    DISPLAY_NAME = "Luminex xPONENT"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = LuminexXponentReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> MapperData:
        reader = LuminexXponentReader(named_file_contents)
        data = Data.create(reader)
        return MapperData(
            create_metadata(
                data.header, data.calibrations, named_file_contents.original_file_path
            ),
            create_measurement_groups(data.measurement_list.measurements, data.header),
        )
