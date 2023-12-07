from __future__ import annotations

from collections.abc import Hashable, Sequence
from typing import Callable, Literal

import pandas as pd
from pandas._libs import lib
from pandas._typing import DtypeArg, FilePath, HashableT, IndexLabel, ReadCsvBuffer


def read_csv(
    filepath_or_buffer: FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str],
    delimiter: str | None | lib.NoDefault = None,
    dtype: DtypeArg | None = None,
    header: int | Sequence[int] | None | Literal["infer"] = "infer",
    index_col: IndexLabel | Literal[False] | None = None,
    names: Sequence[Hashable] | None | lib.NoDefault = lib.no_default,
    nrows: int | None = None,
    parse_dates: bool | Sequence[Hashable] | None = None,
    sep: str | None | lib.NoDefault = lib.no_default,
    skiprows: list[int] | int | Callable[[Hashable], bool] | None = None,
    thousands: str | None = None,
    usecols: list[HashableT] | Callable[[Hashable], bool] | None = None,
) -> pd.DataFrame:
    """
    Read a delimited text file into a Pandas DataFrame.

    Wrap pd.read_csv() -- using only the parameters we need -- to ensure consistent behavior
    across the codebase. pd.read_csv() should only be called directly here.

    Note that this only supports returning a pd.DataFrame.
    """
    # Type ignores are unfortunate. The type hints above were copied directly from pandas src.
    # It's possible that even with importing __annotations__, pandas' newer-style hints
    # don't work as well in 3.9.
    df = pd.read_csv(  # type: ignore[misc]
        filepath_or_buffer,
        delimiter=delimiter,  # type: ignore[arg-type]
        dtype=dtype,
        header=header,
        index_col=index_col,  # type: ignore[arg-type]
        names=names,  # type: ignore[arg-type]
        nrows=nrows,
        parse_dates=parse_dates,  # type: ignore[arg-type]
        sep=sep,  # type: ignore[arg-type]
        skiprows=skiprows,  # type: ignore[arg-type]
        thousands=thousands,
        usecols=usecols,  # type: ignore[arg-type]
    )

    if not isinstance(df, pd.DataFrame):
        msg = "Parameter value(s) resulted in a TextFileReader being returned."
        raise ValueError(msg)
    return df
