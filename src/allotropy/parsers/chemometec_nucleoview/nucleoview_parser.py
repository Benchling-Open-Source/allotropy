from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.chemometec_nucleoview.nucleoview_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows
from allotropy.parsers.vendor_parser import MapperVendorParser


class ChemometecNucleoviewParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "ChemoMetec Nucleoview"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = NucleoviewReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        df = NucleoviewReader.read(named_file_contents.contents)
        return Data(
            create_metadata(
                df_to_series_data(df.head(1)), named_file_contents.original_file_name
            ),
            map_rows(df, create_measurement_groups),
        )
