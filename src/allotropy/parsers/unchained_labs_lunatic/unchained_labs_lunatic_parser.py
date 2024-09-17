from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_reader import (
    UnchainedLabsLunaticReader,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import MapperVendorParser


class UnchainedLabsLunaticParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Unchained Labs Lunatic"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = UnchainedLabsLunaticReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = UnchainedLabsLunaticReader(named_file_contents)
        measurement_groups, calculated_data = create_measurement_groups(
            reader.header, reader.data
        )
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_name),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )
