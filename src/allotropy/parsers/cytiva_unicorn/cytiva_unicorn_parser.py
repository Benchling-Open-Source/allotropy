from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_unicorn.constants import DISPLAY_NAME
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import UnicornFileHandler
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CytivaUnicornParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = "zip"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        handler = UnicornFileHandler(named_file_contents.original_file_path)
        results = handler.get_results()
        return Data(
            create_metadata(handler, results),
            create_measurement_groups(handler, results),
        )
