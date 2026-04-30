import zipfile

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
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
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "zip"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            named_file_contents.contents.seek(0)
            with zipfile.ZipFile(named_file_contents.get_bytes_stream()) as zf:
                return any(name.endswith(".zip") for name in zf.namelist())
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        handler = UnicornZipHandler(named_file_contents.get_bytes_stream())
        results = handler.get_results()
        return Data(
            create_metadata(handler, results, named_file_contents.original_file_path),
            create_measurement_groups(handler, results),
        )
