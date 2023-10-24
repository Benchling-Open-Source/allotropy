from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from allotropy.parsers.lines_reader import CsvReader


def df_to_series(df: pd.DataFrame) -> pd.Series:
    df.columns = df.iloc[0]  # type: ignore[assignment]
    return pd.Series(df.iloc[-1], index=df.columns)


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


@dataclass
class BasicAssayInfo:
    protocol_id: str
    assay_id: str

    @staticmethod
    def create() -> BasicAssayInfo:
        return BasicAssayInfo(
            protocol_id="",  # FIXME
            assay_id="",  # FIXME
        )


@dataclass
class Instrument:
    serial_number: str
    nickname: str

    @staticmethod
    def create() -> Instrument:
        return Instrument(serial_number="", nickname="")  # FIXME


@dataclass
class Result:
    col: str
    row: str
    value: float


@dataclass
class Plate:
    number: str
    results: list[Result]

    @staticmethod
    def create(reader: CsvReader) -> list[Plate]:
        data = reader.pop_csv_block()
        cell_data = data.iloc[4:, 1:]
        series = (
            cell_data.drop(0, axis=0).drop(0, axis=1)
            if cell_data.iloc[1, 0] == "A"
            else cell_data
        )
        rows, cols = series.shape
        series.index = [num_to_chars(i) for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(i).zfill(2) for i in range(1, cols + 1)]  # type: ignore[assignment]

        return [
            Plate(
                number=0,
                results=[
                    Result(col, row, float(series.loc[col, row]))
                    for col, row in series.stack().index
                ],
            )
        ]


@dataclass
class Data:
    plates: list[Plate]
    number_of_wells: Optional[float]
    basic_assay_info: BasicAssayInfo
    instrument: Instrument

    @staticmethod
    def create(reader: CsvReader) -> Data:
        plates = Plate.create(reader)
        return Data(
            plates=plates,
            number_of_wells=len(plates[0].results),
            basic_assay_info=BasicAssayInfo.create(),
            instrument=Instrument.create(),
        )
