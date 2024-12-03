from functools import partial

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.tecan_magellan.constants import DISPLAY_NAME
from allotropy.parsers.tecan_magellan.tecan_magellan_reader import (
    TecanMagellanReader,
)
from allotropy.parsers.tecan_magellan.tecan_magellan_structure import (
    create_measurement_groups,
    create_metadata,
    MagellanMetadata,
)
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class TecanMagellanParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = TecanMagellanReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = TecanMagellanReader(named_file_contents)
        metadata = MagellanMetadata.create(reader.metadata_lines)
        well_count = len(reader.data)

        return Data(
            create_metadata(metadata, named_file_contents.original_file_path),
            map_rows(
                reader.data,
                partial(
                    create_measurement_groups, metadata=metadata, well_count=well_count
                ),
            ),
        )
