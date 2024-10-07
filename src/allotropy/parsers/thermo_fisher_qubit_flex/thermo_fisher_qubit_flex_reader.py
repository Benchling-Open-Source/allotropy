"""" Reader file for Thermo Fisher Qubit Flex Parser"""

import numpy as np
import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv, read_excel


class ThermoFisherQubitFlexReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"

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
        if named_file_contents.extension == "csv":
            df = read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        else:
            df = read_excel(named_file_contents.contents)
        df = df.replace(np.nan, None)
        return df
