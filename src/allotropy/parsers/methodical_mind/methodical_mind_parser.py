from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.methodical_mind.methodical_mind_reader import (
    MethodicalMindReader,
)
from allotropy.parsers.methodical_mind.methodical_mind_structure import (
    create_measurement_groups,
    create_metadata,
    Header,
    PlateData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class MethodicalMindParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Methodical Mind"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = MethodicalMindReader(named_file_contents)
        return Data(
            create_metadata(Header.create(reader.plate_headers[0])),
            create_measurement_groups(
                [PlateData.create(header, data) for header, data in reader]
            ),
        )
