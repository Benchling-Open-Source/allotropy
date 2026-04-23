import re

import pandas as pd

from allotropy.allotrope.models.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_echo_plate_reformat.beckman_echo_plate_reformat_reader import (
    BeckmanEchoPlateReformatReader,
)
from allotropy.parsers.beckman_echo_plate_reformat.beckman_echo_plate_reformat_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.beckman_echo_plate_reformat.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BeckmanEchoPlateReformatParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BeckmanEchoPlateReformatReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            for line in lines[:20]:
                if re.match(r"^\[.+\]", line):
                    return True
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BeckmanEchoPlateReformatReader(named_file_contents)
        measurement_groups = create_measurement_groups(
            pd.concat(reader.sections.values(), ignore_index=True), reader.header
        )
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            measurement_groups,
        )
