import io

import pandas as pd


class ViCellBluReader:
    @classmethod
    def read(cls, contents: io.IOBase) -> pd.DataFrame:
        return pd.read_csv(contents, index_col=False)  # type: ignore[call-overload]
