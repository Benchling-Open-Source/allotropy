from __future__ import annotations

import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv, read_excel, SeriesData


class NexcelomMatrixReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:

        if named_file_contents.extension == "csv":
            df = read_csv(
                named_file_contents.contents,
                encoding=DEFAULT_ENCODING,
            )
        else:
            df = read_excel(named_file_contents.contents)

        self.data = df
