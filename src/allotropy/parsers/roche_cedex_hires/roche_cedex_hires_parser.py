from allotropy.allotrope.models.adm.cell_counting.rec._2024._09.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_hires.constants import DISPLAY_NAME
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_reader import (
    RocheCedexHiResReader,
)
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexHiResParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = RocheCedexHiResReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = RocheCedexHiResReader(named_file_contents)
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            map_rows(reader.data, create_measurement_groups),
        )
