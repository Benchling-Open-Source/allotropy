from allotropy.allotrope.models.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_handler.benchling._2024._11.liquid_handler import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_coulter_biomek.beckman_coulter_biomek_reader import (
    BeckmanCoulterBiomekReader,
)
from allotropy.parsers.beckman_coulter_biomek.beckman_coulter_biomek_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.beckman_coulter_biomek.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BeckmanCoulterBiomekParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BeckmanCoulterBiomekReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BeckmanCoulterBiomekReader(named_file_contents)
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(reader.data, reader.header),
        )
