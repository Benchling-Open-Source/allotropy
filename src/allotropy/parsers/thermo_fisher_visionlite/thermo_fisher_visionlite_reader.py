import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.thermo_fisher_visionlite.constants import (
    HEADER_COLS,
    SAMPLE_NAME_COLS,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_not_none


class ThermoFisherVisionliteReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData | None = None
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))

        if (first_line := reader.get()) is None:
            msg = "Unable to get data, empty file."
            raise AllotropeConversionError(msg)

        expected_required_columns = ("sample name", "well position")
        # If the first line in the file does not contain one of the required columns for QUANT or FIXED
        # experiments, then we expect the experiment type to be SCAN or KINETIC, and the first line to be a
        # header with comma separated key value pairs.
        if all(
            col_name not in first_line.lower() for col_name in expected_required_columns
        ):
            columns = first_line.split(",")[:4]
            if len(columns) != len(HEADER_COLS):
                msg = f"Expected {len(HEADER_COLS)} columns, but got {len(columns)}:columns"
                raise AllotropeConversionError(msg)
            self.header = SeriesData(pd.Series(columns, index=HEADER_COLS))
            reader.pop()

        sep = "\t" if "\t" in first_line else ","
        data = assert_not_none(
            reader.pop_csv_block_as_df(
                header="infer", sep=sep, dtype={col: str for col in SAMPLE_NAME_COLS}
            )
        )
        self.data = data.replace(np.nan, None)
