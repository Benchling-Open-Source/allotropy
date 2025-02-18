from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_chromeleon.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_chromeleon.thermo_fisher_chromeleon_reader import (
    ThermoFisherChromeleonReader,
)
from allotropy.parsers.thermo_fisher_chromeleon.thermo_fisher_chromeleon_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherChromeleonParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherChromeleonReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = ThermoFisherChromeleonReader(named_file_contents)
        return Data(
            create_metadata(
                reader.injections[0],
                reader.sequence,
                reader.device_information,
                named_file_contents.original_file_path,
            ),
            create_measurement_groups(reader.injections),
        )
