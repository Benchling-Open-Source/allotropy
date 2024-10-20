import numpy as np

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    create_measurement_groups,
    create_metadata,
    SampleList,
    Title,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import read_csv
from allotropy.parsers.vendor_parser import VendorParser


class NovaBioFlexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "NovaBio Flex2"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "csv"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        # NOTE: calling parse_dates and removing NaN clears empty rows.
        data = read_csv(
            named_file_contents.contents, parse_dates=["Date & Time"]
        ).replace(np.nan, None)
        title = Title.create(named_file_contents.original_file_name)
        sample_list = SampleList.create(data)
        return Data(
            create_metadata(title, named_file_contents.original_file_name),
            create_measurement_groups(title, sample_list),
        )
