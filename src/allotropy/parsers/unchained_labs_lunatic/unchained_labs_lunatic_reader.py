from io import IOBase

import numpy as np
import pandas as pd


class UnchainedLabsLunaticReader:
    def __init__(self, contents: IOBase):
        self.data = pd.read_csv(  # type: ignore[call-overload]
            filepath_or_buffer=contents
        ).replace(np.nan, None)
