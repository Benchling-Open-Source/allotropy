from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.ctl_immunospot.ctl_immunospot_reader import CtlImmunospotReader
from allotropy.parsers.ctl_immunospot.ctl_immunospot_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "CTL ImmunoSpot"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = CtlImmunospotReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = CtlImmunospotReader(named_file_contents)
        return Data(
            create_metadata(reader.header),
            create_measurement_groups(
                reader.header,
                reader.plate_identifier,
                reader.plate_data,
                reader.histograms,
            ),
        )
