"""Parser for Thermo Fisher Diomni."""

from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser

from allotropy.parsers.thermo_fisher_diomni.thermo_fisher_diomni_reader import (
    ThermoFisherDiomniReader,
)
from allotropy.parsers.thermo_fisher_diomni.thermo_fisher_diomni_structure import (
    create_metadata,
    create_measurement_groups,
)


class ThermoFisherDiomniParser(VendorParser[Data, Model]):
    """Parser for Thermo Fisher Diomni files."""

    DISPLAY_NAME = "Thermo Fisher Diomni"
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = ThermoFisherDiomniReader.SUPPORTED_EXTENSIONS
    SUPPORTED_DETECTION_MODES = "Fluorescence"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        """Create Data object from input file."""
        reader = ThermoFisherDiomniReader(named_file_contents)

        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(reader.header, reader.measurements),
        )
