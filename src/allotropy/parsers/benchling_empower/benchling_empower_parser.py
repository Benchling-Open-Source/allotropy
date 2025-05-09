from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.benchling_empower.benchling_empower_reader import (
    BenchlingEmpowerReader,
)
from allotropy.parsers.benchling_empower.benchling_empower_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.benchling_empower.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BenchlingEmpowerParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BenchlingEmpowerReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BenchlingEmpowerReader(named_file_contents)

        return Data(
            create_metadata(
                reader.metadata_fields,
                reader.injections[0],
                named_file_contents.original_file_path,
            ),
            create_measurement_groups(
                reader.injections,
                reader.metadata_fields,
            ),
        )
