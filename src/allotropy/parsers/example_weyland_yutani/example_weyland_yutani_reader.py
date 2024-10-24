import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, EMPTY_CSV_LINE, read_to_lines


class ExampleWeylandYutaniReader:
    SUPPORTED_EXTENSIONS = "csv"

    middle: pd.DataFrame | None
    bottom: pd.DataFrame | None

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))
        _ = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)
        self.middle = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)
        self.bottom = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)
