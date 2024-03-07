import numpy as np
import pandas as pd

from allotropy.types import IOType


class QiacuitydPCRReader:
    def __init__(self, contents: IOType):
        # Read in the file, skip first row since it does not have data in it.
        qiacuity_dpcr_data = pd.read_csv(filepath_or_buffer=contents, header=1).replace(
            np.nan, None
        )
        column_names = qiacuity_dpcr_data.columns.tolist()
        # Rename the blank column to specify that it's the Well Name column
        column_names[0] = "Well Name"
        column_index = pd.Index(column_names)
        qiacuity_dpcr_data.columns = column_index
        self.well_data = qiacuity_dpcr_data
