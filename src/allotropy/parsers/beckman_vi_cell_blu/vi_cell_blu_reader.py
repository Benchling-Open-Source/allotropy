import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class ViCellBluReader:
    SUPPORTED_EXTENSIONS = "csv"

    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        return read_csv(
            named_file_contents.contents,
            index_col=False,
            encoding=named_file_contents.encoding,
        )
