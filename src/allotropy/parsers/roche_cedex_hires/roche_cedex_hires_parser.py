""" Parser file for Roche Cedex HiRes Instrument """
from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_reader import (
    RocheCedexHiResReader,
)
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows
from allotropy.parsers.vendor_parser import MapperVendorParser


class RocheCedexHiResParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Roche Cedex HiRes"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        df = RocheCedexHiResReader.read(named_file_contents)
        return Data(
            create_metadata(
                df_to_series_data(df.head(1)), named_file_contents.original_file_name
            ),
            map_rows(df, create_measurement_groups),
        )
