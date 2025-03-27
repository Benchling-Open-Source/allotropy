from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import Data, Mapper
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cfxmaestro.cfxmaestro_reader import (
    CFXMaestroReader,
)
from allotropy.parsers.cfxmaestro.cfxmaestro_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.cfxmaestro.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CfxmaestroParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = CFXMaestroReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = CFXMaestroReader(named_file_contents)
        return Data(
            create_metadata(named_file_contents.original_file_path),
            create_measurement_groups(reader.data),
        )
