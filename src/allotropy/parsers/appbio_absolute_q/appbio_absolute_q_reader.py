import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class AppbioAbsoluteQReader:
    SUPPORTED_EXTENSIONS = "csv"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        df = read_csv(named_file_contents.contents)

        if "Name" in df and "Sample" not in df:
            df = df.rename(columns={"Name": "Sample"})

        if "Sample" not in df:
            msg = "Input is missing required column 'Sample' or 'Name'."
            raise AllotropeConversionError(msg)

        self.data = df.replace(np.nan, None)
