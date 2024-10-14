from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import VendorParser


class KaleidoParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Revvity Kaleido"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    SUPPORTED_EXTENSIONS = "csv"

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        data = create_data(CsvReader(read_to_lines(named_file_contents)))
        return Data(
            create_metadata(data, named_file_contents.original_file_path),
            create_measurement_groups(data),
        )
