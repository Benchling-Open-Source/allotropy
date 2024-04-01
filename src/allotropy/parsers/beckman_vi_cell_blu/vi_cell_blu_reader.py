import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.values import assert_not_none


class ViCellBluReader:
    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        return assert_not_none(
            reader.pop_csv_block_as_df(index_col=False, header=0),
            msg=f"Unable to read csv file '{named_file_contents.original_file_name}'.",
        )
