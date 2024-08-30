from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_one.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_nanodrop_one.thermo_fisher_nanodrop_one_structure import (
    DataNanodrop,
)
from allotropy.parsers.utils.pandas import read_multisheet_excel
from allotropy.parsers.vendor_parser import MapperVendorParser


class ThermoFisherNanodropOneParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "xlsx"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        contents = read_multisheet_excel(
            named_file_contents.contents,
            engine="calamine",
        )
        return DataNanodrop.create(contents, named_file_contents.original_file_name)
