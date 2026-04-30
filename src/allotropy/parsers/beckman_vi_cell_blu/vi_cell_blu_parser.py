from __future__ import annotations

from allotropy.allotrope.models.adm.cell_counting.rec._2024._09.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_reader import ViCellBluReader
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class ViCellBluParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Beckman Coulter Vi-Cell BLU"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ViCellBluReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            if isinstance(raw, bytes):
                if raw[:2] == b"\xff\xfe":
                    text = raw[2:].decode("utf-16-le", errors="replace")
                elif raw[:2] == b"\xfe\xff":
                    text = raw[2:].decode("utf-16-be", errors="replace")
                else:
                    text = raw.decode("utf-8", errors="replace")
            else:
                text = raw
            lines = text.splitlines()
            if not lines:
                return False
            header = lines[0]
            return "Viability (%)" in header and "Viable (x10^6) cells/mL" in header
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        return Data(
            create_metadata(named_file_contents.original_file_path),
            map_rows(
                ViCellBluReader.read(named_file_contents), create_measurement_group
            ),
        )
