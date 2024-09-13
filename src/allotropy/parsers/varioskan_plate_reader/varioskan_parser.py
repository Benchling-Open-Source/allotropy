from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import read_multisheet_excel
from allotropy.parsers.varioskan_plate_reader.varioskan_structure import DataVarioskan
from allotropy.parsers.vendor_parser import MapperVendorParser


class VarioskanParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Varioskan"
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = "xlsx"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        contents = read_multisheet_excel(
            named_file_contents.contents, engine="calamine"
        )
        return DataVarioskan.create(
            sheet_data=contents, file_name=named_file_contents.original_file_name
        )
