"""Reader file for Roche Cedex HiRes Instrument"""

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv, read_excel
from allotropy.constants import DEFAULT_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.roche_cedex_hires import constants


class RocheCedexHiResReader:
    """
    A reader class for parsing Roche Cedex HiRes data files into pandas DataFrames.

    Methods:
    read(named_file_contents: NamedFileContents) -> pd.DataFrame:
        Reads the content of the provided named file and returns it as a pandas DataFrame.
    """

    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        """
        Reads the content of the provided named file and returns it as a pandas DataFrame.

        Parameters:
        named_file_contents (NamedFileContents): The named file contents to read.
            It includes the original file name, file contents, and encoding.

        Returns:
        pd.DataFrame: The content of the file as a pandas DataFrame.

        Raises:
        AllotropeConversionError: If the file format is not supported.
        """
        if named_file_contents.original_file_name.endswith(".csv"):
            return read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        elif named_file_contents.original_file_name.endswith(".xlsx"):
            return read_excel(named_file_contents.contents.name)
        else:
            message = f"{constants.UNSUPPORTED_FILE_FORMAT_ERROR} '{named_file_contents.original_file_name}'"
            raise AllotropeConversionError(message)
