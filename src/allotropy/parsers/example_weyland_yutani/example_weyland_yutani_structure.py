from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from allotropy.parsers.lines_reader import CsvReader


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
    def create(header: str | None) -> Instrument:
        if header is None:
            return Instrument(serial_number="", nickname="")

        instrument_spec = header.strip(",").split(" ")
        serial_number = " ".join(instrument_spec[0:2])
        nickname = instrument_spec[2]

        return Instrument(serial_number=serial_number, nickname=nickname)


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
        cell_data = data.iloc[4:, 1:].T
        series = (
            cell_data.drop(0, axis=0).drop(0, axis=1)
            if cell_data.iloc[1, 0] == "A"
            else cell_data
        )
        rows, cols = series.shape
        series.index = [data.iloc[3, i + 1] for i in range(rows)]  # type: ignore[assignment]
        series.columns = [str(data.iloc[3 + i, 0]) for i in range(1, cols + 1)]  # type: ignore[assignment]
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
        instrument = Instrument.create(reader.get())
        plates = Plate.create(reader)
        return Data(
            plates=plates,
            number_of_wells=len(plates[0].results),
            basic_assay_info=BasicAssayInfo.create(),
            instrument=instrument,
        )
