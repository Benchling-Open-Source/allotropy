from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.ctl_immunospot.ctl_immunospot_structure import (
    AssayData,
    create_measurement_groups,
    create_metadata,
    Header,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "CTL ImmunoSpot"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = LinesReader.create(named_file_contents)
        header = Header.create(reader)
        reader.drop_empty()
        reader.drop_until_empty()  # ignore assay info
        reader.drop_empty()
        assay_data = AssayData.create(reader)

        return Data(
            create_metadata(header),
            create_measurement_groups(assay_data, header),
        )
