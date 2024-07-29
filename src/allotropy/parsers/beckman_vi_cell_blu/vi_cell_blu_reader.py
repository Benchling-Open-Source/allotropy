import unicodedata

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
        ).rename(columns=cls._normalize_column_names)

    @classmethod
    def _normalize_column_names(cls, col: str) -> str:
        """Normalize column names that look the same but have mismatching characters

        Some column names in the instrument files include two different `µ` characters that look the same,
        the Micro Sign (U+00B5) and the Greek Small letter mu (U+03BC), this mapper uses the unicode `NFKC`
        normalization to ensure consistency when retrieving values from those columns.
        """
        return unicodedata.normalize("NFKC", col)
