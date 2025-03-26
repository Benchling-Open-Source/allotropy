import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class QiacuitydPCRReader:
    SUPPORTED_EXTENSIONS = "csv"
    well_data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents):
        # Read in the file, skip first row since it does not have data in it.
        qiacuity_dpcr_data = read_csv(
            filepath_or_buffer=named_file_contents.contents,
            header=1,
            encoding=named_file_contents.encoding,
        ).replace(np.nan, None)
        qiacuity_dpcr_data.columns = qiacuity_dpcr_data.columns.str.replace("�", "μ")
        qiacuity_dpcr_data.columns = qiacuity_dpcr_data.columns.str.replace("Âμ", "μ")
        column_names = qiacuity_dpcr_data.columns.tolist()
        # Rename the blank column to specify that it's the Well Name column
        column_names[0] = "Well Name"
        column_index = pd.Index(column_names)
        qiacuity_dpcr_data.columns = column_index
        self.well_data = qiacuity_dpcr_data
