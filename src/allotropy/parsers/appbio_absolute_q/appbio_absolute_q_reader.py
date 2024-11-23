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

        columns_to_rename = {}
        if "Name" in df and "Sample" not in df:
            columns_to_rename["Name"] = "Sample"
        if "Well ID" in df and "Well" not in df:
            columns_to_rename["Well ID"] = "Well"

        if columns_to_rename:
            df = df.rename(columns=columns_to_rename)

        required_keys = {"Sample"}
        for key in required_keys:
            if key not in df:
                possible_keys = key
                if key in columns_to_rename:
                    possible_keys += f" or {columns_to_rename[key]}"
                msg = f"Input is missing required column '{possible_keys}'"
                raise AllotropeConversionError(msg)

        self.data = df.replace(np.nan, None)
