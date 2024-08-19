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
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.vendor_parser import MapperVendorParser


class CtlImmunospotParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "CTL ImmunoSpot"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper

    def _create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = LinesReader.create(named_file_contents)
        metadata = create_metadata(reader)
        reader.drop_empty()
        reader.drop_until_empty()  # ignore assay info
        reader.drop_empty()
        assay_data = AssayData.create(reader)

        return Data(
            metadata,
            create_measurement_groups(assay_data, assert_not_none(metadata.file_name)),
        )
