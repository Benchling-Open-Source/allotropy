from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.benchling_chromeleon.benchling_chromeleon_reader import (
    BenchlingChromeleonReader,
)
from allotropy.parsers.benchling_chromeleon.benchling_chromeleon_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.benchling_chromeleon.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BenchlingChromeleonParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BenchlingChromeleonReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BenchlingChromeleonReader(named_file_contents)
        return Data(
            create_metadata(
                reader.injections[0],
                reader.sequence,
                named_file_contents.original_file_path,
                reader.device_information,
            ),
            create_measurement_groups(reader.injections),
        )
