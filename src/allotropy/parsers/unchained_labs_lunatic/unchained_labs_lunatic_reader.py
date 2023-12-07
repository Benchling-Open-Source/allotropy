import numpy as np
import pandas as pd

from allotropy.types import IOType


class UnchainedLabsLunaticReader:
    @staticmethod
    def read(contents: IOType) -> pd.DataFrame:
        data: pd.DataFrame = pd.read_csv(filepath_or_buffer=contents)

        return data.replace(np.nan, None)
