from functools import partial

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_reader import (
    BmgLabtechSmartControlReader,
)
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_structure import (
    create_calculated_data_documents,
    create_metadata,
    map_measurement_group,
)
from allotropy.parsers.bmg_labtech_smart_control.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class BmgLabtechSmartControlParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BmgLabtechSmartControlReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BmgLabtechSmartControlReader(named_file_contents)
        measurement_groups = map_rows(
            reader.data, partial(map_measurement_group, headers=reader.header)
        )
        return Data(
            create_metadata(named_file_contents.original_file_path, reader.header),
            measurement_groups,
            create_calculated_data_documents(measurement_groups, reader),
        )
