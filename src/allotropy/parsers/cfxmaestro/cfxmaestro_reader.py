from __future__ import annotations

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class CFXMaestroReader:
    SUPPORTED_EXTENSIONS = "csv"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        self.data = read_csv(named_file_contents.contents)
