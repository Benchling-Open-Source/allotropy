import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.nexcelom_matrix.constants import (
    MILLION_CONVERSION,
    MILLION_SCALE_COLS,
)
from allotropy.parsers.utils.pandas import (
    read_csv,
    read_excel,
)


class NexcelomMatrixReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> pd.DataFrame:
        if named_file_contents.extension == "csv":
            df = read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        else:
            df = read_excel(named_file_contents.contents)

        df[MILLION_SCALE_COLS] = df[MILLION_SCALE_COLS].applymap(lambda x: x / MILLION_CONVERSION)
        self.data = df
