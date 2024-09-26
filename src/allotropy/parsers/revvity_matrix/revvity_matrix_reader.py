import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.revvity_matrix.constants import (
    MILLION_CONVERSION,
    MILLION_SCALE_COLS,
)
from allotropy.parsers.utils.pandas import (
    read_excel,
)


class RevvityMatrixReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        df = read_excel(named_file_contents.contents)

        df[MILLION_SCALE_COLS] = df[MILLION_SCALE_COLS].map(
            lambda x: x / MILLION_CONVERSION
        )
        self.data = df
