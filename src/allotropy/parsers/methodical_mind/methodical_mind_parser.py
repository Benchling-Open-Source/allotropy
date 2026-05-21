from __future__ import annotations

import re

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
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
from allotropy.parsers.vendor_parser import VendorParser


class MethodicalMindParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "MSD Methodical Mind"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read()
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            return any(re.match(r"^=+Data=+$", line) for line in lines[:50])
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = MethodicalMindReader(named_file_contents)
        return Data(
            create_metadata(
                Header.create(reader.plate_headers[0]),
                named_file_contents.original_file_path,
            ),
            create_measurement_groups(
                [PlateData.create(header, data) for header, data in reader]
            ),
        )
