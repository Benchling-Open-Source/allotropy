from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from allotropy.parsers.lines_reader import CsvReader


@dataclass
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: Optional[str]

    @staticmethod
    def create(df: pd.DataFrame) -> BasicAssayInfo:
        checksum = df.iat[-1, 1] if df.iat[-1, 0] == "Checksum" else None
        return BasicAssayInfo(
            protocol_id="Weyland Yutani Example",
            assay_id="Example Assay",
            checksum=checksum,
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
    def create(df: pd.DataFrame) -> list[Plate]:
        cell_data = df.iloc[4:, 1:].T
        series = (
            cell_data.drop(0, axis=0).drop(0, axis=1)
            if cell_data.iloc[1, 0] == "A"
            else cell_data
        )
        rows, cols = series.shape
        series.index = [df.iloc[3, i + 1] for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(df.iloc[3 + i, 0]) for i in range(1, cols + 1)]  # type: ignore[assignment]
        return [
            Plate(
                number="0",
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
        df = reader.pop_csv_block()
        plates = Plate.create(df)
        return Data(
            plates=plates,
            number_of_wells=len(plates[0].results),
            basic_assay_info=BasicAssayInfo.create(df),
            instrument=Instrument.create(),
        )
