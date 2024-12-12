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
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser

import pandas as pd


class BeckmanEchoPlateReformatParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = BeckmanEchoPlateReformatReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BeckmanEchoPlateReformatReader(named_file_contents)
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(pd.concat(reader.sections.values(), ignore_index=True), reader.header),
        )
