import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.thermo_fisher_visionlite.constants import HEADER_COLS
from allotropy.parsers.utils.pandas import SeriesData


class ThermoFisherVisionliteReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData | None = None
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))
        # try to get the header data (Scan and Kinetic files)

        first_line = reader.get()
        if first_line is not None and not first_line.startswith("Sample Name"):
            self.header = SeriesData(
                pd.Series(first_line.split(",")[:4], index=HEADER_COLS)
            )
            reader.pop()

        data = reader.pop_csv_block_as_df(header="infer")
        if data is None:
            msg = "Unable to get data, empty file."
            raise AllotropeConversionError(msg)
        self.data = data.replace(np.nan, None)
