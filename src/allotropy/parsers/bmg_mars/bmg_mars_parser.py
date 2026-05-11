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
from allotropy.parsers.bmg_mars.bmg_mars_reader import BmgMarsReader
from allotropy.parsers.bmg_mars.bmg_mars_structure import (
    create_measurement_groups,
    create_metadata,
    Header,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BmgMarsParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "BMG Labtech MARS"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "csv"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read()
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            has_key_value = False
            has_raw_data = False
            for line in lines[:30]:
                if re.match(r"^.+:\s+.+", line):
                    has_key_value = True
                    break
            for line in lines:
                stripped = line.strip()
                if stripped == "Raw Data" or stripped.startswith("Raw Data"):
                    has_raw_data = True
                    break
            return has_key_value and has_raw_data
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BmgMarsReader(named_file_contents)
        header = Header.create(reader.header, reader.header_content)
        return Data(
            create_metadata(header, named_file_contents.original_file_path),
            create_measurement_groups(reader.data, header),
        )
