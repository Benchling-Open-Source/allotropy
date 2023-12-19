from __future__ import annotations

from collections.abc import Hashable, MutableSequence, Sequence
from typing import Callable, Literal, Optional

import pandas as pd
from pandas._libs import lib
from pandas._typing import DtypeArg, FilePath, ReadCsvBuffer


def read_csv(
    filepath_or_buffer: FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str],
    delimiter: Optional[str] = None,
    dtype: DtypeArg | None = None,
    float_precision: Literal["high", "legacy", "round_trip"] | None = None,
    header: int | Sequence[int] | None | Literal["infer"] = "infer",
    index_col: Optional[Literal[False]] = None,
    names: Sequence[Hashable] | None | lib.NoDefault = lib.no_default,
    nrows: int | None = None,
    parse_dates: bool | Sequence[Hashable] | None = None,
    sep: str | None | lib.NoDefault = lib.no_default,
    skipinitialspace: bool = False,  # noqa: FBT001, FBT002
    skiprows: list[int] | int | Callable[[Hashable], bool] | None = None,
    skipfooter: int = 0,
    thousands: str | None = None,
    usecols: Sequence[int] | MutableSequence[str] | None = None,
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
        delimiter=delimiter,
        dtype=dtype,
        float_precision=float_precision,
        header=header,
        index_col=index_col,
        names=names,  # type: ignore[arg-type]
        nrows=nrows,
        parse_dates=parse_dates,  # type: ignore[arg-type]
        sep=sep,  # type: ignore[arg-type]
        skipinitialspace=skipinitialspace,
        skiprows=skiprows,  # type: ignore[arg-type]
        skipfooter=skipfooter,
        thousands=thousands,
        usecols=usecols,
    )

    if not isinstance(df, pd.DataFrame):
        msg = "Parameter value(s) resulted in a TextFileReader being returned."
        raise ValueError(msg)
    return df
