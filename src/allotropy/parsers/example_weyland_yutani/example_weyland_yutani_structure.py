from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader

EMPTY_CSV_LINE = r"^,*$"
PROTOCOL_ID = "Weyland Yutani Example"
ASSAY_ID = "Example Assay"


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: Optional[str]

    @staticmethod
    def create(bottom: Optional[pd.DataFrame]) -> BasicAssayInfo:
        checksum = (
            None
            if (bottom is None) or (bottom.iloc[0, 0] != "Checksum")
            else str(bottom.iloc[0, 1])
        )
        return BasicAssayInfo(
            protocol_id=PROTOCOL_ID,
            assay_id=ASSAY_ID,
            checksum=checksum,
        )


@dataclass(frozen=True)
class Instrument:
    serial_number: str
    nickname: str

    # TODO: extract and fill in real values for serial number and nickname
    @staticmethod
    def create() -> Instrument:
        return Instrument(serial_number="", nickname="")


@dataclass(frozen=True)
class Result:
    col: str
    row: str
    value: float


@dataclass(frozen=True)
class Plate:
    number: str
    results: list[Result]

    @staticmethod
    def create(df: Optional[pd.DataFrame]) -> list[Plate]:
        if df is None:
            return []
        pivoted = df.T
        if pivoted.iloc[1, 0] != "A":
            msg = "Column header(s) not found."
            raise AllotropeConversionError(msg)
        stripped = pivoted.drop(0, axis=0).drop(0, axis=1)
        rows, cols = stripped.shape
        stripped.index = [df.iloc[0, i + 1] for i in range(rows)]  # type: ignore
        stripped.columns = [str(int(df.iloc[i, 0])) for i in range(1, cols + 1)]  # type: ignore
        return [
            Plate(
                number="0",
                results=[
                    Result(col, row, float(stripped.loc[col, row]))
                    for col, row in stripped.stack().index
                ],
            )
        ]


@dataclass(frozen=True)
class Data:
    plates: list[Plate]
    number_of_wells: Optional[float]
    basic_assay_info: BasicAssayInfo
    instrument: Instrument

    @staticmethod
    def create(reader: CsvReader) -> Data:
        _ = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)
        middle = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)
        bottom = reader.pop_csv_block_as_df(empty_pat=EMPTY_CSV_LINE)

        plates = Plate.create(middle)
        return Data(
            basic_assay_info=BasicAssayInfo.create(bottom),
            plates=plates,
            number_of_wells=len(plates[0].results),
            instrument=Instrument.create(),
        )
