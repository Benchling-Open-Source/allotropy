import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.values import assert_not_none


class MSDWorkbenchReader:
    SUPPORTED_EXTENSIONS = "csv"
    plate_data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension not in self.SUPPORTED_EXTENSIONS:
            msg = f"Unsupported file extension {named_file_contents.extension}"
            raise ValueError(msg)
        file_lines = read_to_lines(named_file_contents)
        reader = CsvReader(file_lines)
        csv_lines = reader.pop_csv_block_as_df()
        data = assert_not_none(csv_lines, "Luminescence data table")
        data = data.dropna(axis=1, how="all")
        data = data.where(pd.notna(data), None)
        self.plate_data = data
