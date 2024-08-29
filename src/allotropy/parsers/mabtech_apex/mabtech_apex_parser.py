from functools import partial

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.mabtech_apex.mabtech_apex_reader import MabtechApexReader
from allotropy.parsers.mabtech_apex.mabtech_apex_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import MapperVendorParser


class MabtechApexParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Mabtech Apex"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = MabtechApexReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = MabtechApexReader.create(named_file_contents)

        # if Read Date is not present in file, return None, no measurement for given Well
        plate_data = reader.data.dropna(subset="Read Date")
        return Data(
            create_metadata(reader.plate_info, named_file_contents.original_file_name),
            map_rows(
                plate_data,
                partial(create_measurement_group, plate_info=reader.plate_info),
            ),
        )
