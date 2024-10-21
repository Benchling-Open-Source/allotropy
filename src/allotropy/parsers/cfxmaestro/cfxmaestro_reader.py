from __future__ import annotations

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class CFXMaestroReader:
    SUPPORTED_EXTENSIONS = "csv"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        # Example of one way to parse data. This may work if your data is a simple dataset,
        # but will probably need some modification, or a totally different approach if the input
        # file is a different format.
        self.data = read_csv(named_file_contents.contents)
