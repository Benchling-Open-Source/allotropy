import numpy as np

from allotropy.allotrope.models.adm.solution_analyzer.benchling._2024._09.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.benchling._2024._09.solution_analyzer import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import (
    create_measurement_groups,
    create_metadata,
    SampleData,
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
        try:
            data = read_csv(
                named_file_contents.contents, parse_dates=["Date & Time"]
            ).replace(np.nan, None)
        except Exception as e:
            # Check if error is about missing Date & Time column
            if "Date & Time" in str(e):
                msg = "Missing 'Date & Time' column in the CSV file. This is required for NovaBio Flex2 files."
                raise AllotropeConversionError(msg) from e
            else:
                msg = f"Failed to parse CSV file: {e}"
                raise AllotropeConversionError(msg) from e

        title = Title.create(named_file_contents.original_file_path)
        sample_data = SampleData.create(data)
        return Data(
            create_metadata(title, named_file_contents.original_file_path),
            create_measurement_groups(title, sample_data.sample_list),
        )
