from io import BytesIO

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cytiva_unicorn.constants import DISPLAY_NAME
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurement_group import (
    create_measurement_groups,
)
from allotropy.parsers.cytiva_unicorn.structure.metadata import (
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CytivaUnicornParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = "zip"
    SCHEMA_MAPPER = Mapper

    def get_bytes_stream(self, named_file_contents: NamedFileContents) -> BytesIO:
        raw_content = named_file_contents.contents.read()
        if isinstance(raw_content, str):
            msg = f"adpater {DISPLAY_NAME} received a str input, which is invalid"
            raise AllotropeConversionError(msg)
        return BytesIO(raw_content)

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        stream = self.get_bytes_stream(named_file_contents)
        handler = UnicornZipHandler(stream)
        results = handler.get_results()
        return Data(
            create_metadata(handler, results),
            create_measurement_groups(handler, results),
        )
