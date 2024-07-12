"""Reader file for ThermoFisher Qubit 4 Adapter"""

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv, read_excel
from allotropy.constants import DEFAULT_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.thermo_fisher_qubit4 import constants


class ThermoFisherQubit4Reader:
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
        if named_file_contents.original_file_name.endswith(".xlsx"):
            dataframe = read_excel(named_file_contents.contents.name)
        elif named_file_contents.original_file_name.endswith(".csv"):
            dataframe = read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        else:
            message = f"{constants.UNSUPPORTED_FILE_FORMAT_ERROR} '{named_file_contents.original_file_name}'"
            raise AllotropeConversionError(message)
        columns = dataframe.columns.tolist()
        new_columns = [
            f"Units_{columns[i - 1]}" if "Units" in col else col
            for i, col in enumerate(columns)
        ]
        dataframe.columns = pd.Index(new_columns)
        return dataframe
