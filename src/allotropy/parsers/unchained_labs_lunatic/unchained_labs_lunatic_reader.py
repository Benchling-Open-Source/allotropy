from io import IOBase

import numpy as np
import pandas as pd


class UnchainedLabsLunaticReader:
    @staticmethod
    def read(contents: IOBase) -> pd.DataFrame:
        data: pd.DataFrame = pd.read_csv(  # type: ignore[call-overload]
            filepath_or_buffer=contents
        ).replace(np.nan, None)

        return data
