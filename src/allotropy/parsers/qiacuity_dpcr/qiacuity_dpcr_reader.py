import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import determine_encoding
from allotropy.parsers.utils.pandas import read_csv


class QiacuitydPCRReader:
    SUPPORTED_EXTENSIONS = "csv"
    well_data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents):
        # Read in the file, skip first row since it does not have data in it.
        contents = named_file_contents.contents.read()
        encoding = (
            determine_encoding(contents, named_file_contents.encoding)
            if isinstance(contents, bytes)
            else None
        )
        named_file_contents.contents.seek(0)
        qiacuity_dpcr_data = read_csv(
            filepath_or_buffer=named_file_contents.contents, header=1, encoding=encoding
        ).replace(np.nan, None)
        qiacuity_dpcr_data.columns = qiacuity_dpcr_data.columns.str.replace("�", "μ")
        qiacuity_dpcr_data.columns = qiacuity_dpcr_data.columns.str.replace("Âμ", "μ")
        column_names = qiacuity_dpcr_data.columns.tolist()
        # Rename the blank column to specify that it's the Well Name column
        column_names[0] = "Well Name"
        column_index = pd.Index(column_names)
        qiacuity_dpcr_data.columns = column_index
        self.well_data = qiacuity_dpcr_data
