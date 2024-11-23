from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_reader import (
    AppbioAbsoluteQReader,
)
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
    Group,
    Well,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "AppBio AbsoluteQ"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AppbioAbsoluteQReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AppbioAbsoluteQReader(named_file_contents)
        wells = Well.create_wells(reader.data)
        groups = Group.create_rows(reader.data)

        return Data(
            create_metadata(
                wells[0].items[0].instrument_identifier,
                named_file_contents.original_file_path,
            ),
            create_measurement_groups(wells),
            calculated_data=create_calculated_data(
                wells, groups, reader.common_columns
            ),
        )
