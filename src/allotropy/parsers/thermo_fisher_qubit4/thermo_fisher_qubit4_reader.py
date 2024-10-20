"""Reader file for ThermoFisher Qubit 4 Adapter"""

import numpy as np
import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv, read_excel, set_columns


class ThermoFisherQubit4Reader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"

    """
    A reader class for parsing ThermoFisher Qubit 4 data files into pandas DataFrames.

    Methods:
    read(named_file_contents: NamedFileContents) -> pd.DataFrame:
        Reads the content of the provided named file and returns it as a pandas DataFrame.
    """

    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        """
        Reads the content of the provided named file and returns it as a pandas DataFrame.
        Changes the "Units" column to "Units_{previous_column}" for better understanding

        Parameters:
        named_file_contents (NamedFileContents): The named file contents to read.
            It includes the original file name, file contents, and encoding.

        Returns:
        pd.DataFrame: The content of the file as a pandas DataFrame.

        Raises:
        AllotropeConversionError: If the file format is not supported.
        """
        if named_file_contents.extension == "xlsx":
            df = read_excel(named_file_contents.contents)
        else:
            df = read_csv(
                named_file_contents.contents, index_col=False, encoding=DEFAULT_ENCODING
            )

        columns = df.columns.tolist()
        new_columns = [
            f"Units_{columns[i - 1]}" if "Units" in col else col
            for i, col in enumerate(columns)
        ]
        set_columns(df, new_columns)
        df = df.replace(np.nan, None)
        return df
