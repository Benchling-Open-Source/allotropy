import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import determine_encoding


class ViCellBluReader:
    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        contents = named_file_contents.contents.read()
        encoding = (
            determine_encoding(contents, named_file_contents.encoding)
            if isinstance(contents, bytes)
            else None
        )
        named_file_contents.contents.seek(0)
        return read_csv(
            named_file_contents.contents, index_col=False, encoding=encoding
        )
