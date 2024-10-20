from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_matrix.constants import DISPLAY_NAME
from allotropy.parsers.revvity_matrix.revvity_matrix_reader import (
    RevvityMatrixReader,
)
from allotropy.parsers.revvity_matrix.revvity_matrix_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class RevvityMatrixParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = RevvityMatrixReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = RevvityMatrixReader(named_file_contents)
        return Data(
            create_metadata(named_file_contents.original_file_name),
            map_rows(reader.data, create_measurement_group),
        )
