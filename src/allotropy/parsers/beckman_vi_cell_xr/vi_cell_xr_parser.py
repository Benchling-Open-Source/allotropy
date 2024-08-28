from __future__ import annotations

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import create_reader_data
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class ViCellXRParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Beckman Vi-Cell XR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt,xls,xlsx"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader_data = create_reader_data(named_file_contents)
        if not reader_data.data:
            msg = "Cannot parse ASM from empty file."
            raise AllotropeConversionError(msg)

        return Data(
            create_metadata(reader_data, named_file_contents.original_file_name),
            [create_measurement_group(row) for row in reader_data.data],
        )
