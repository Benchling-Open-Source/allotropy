from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from allotropy.parsers.lines_reader import CsvReader


@dataclass
class BasicAssayInfo:
    protocol_id: str
    assay_id: str

    @staticmethod
    def create(reader: CsvReader) -> BasicAssayInfo:
        reader.pop_csv_block()
        return BasicAssayInfo(
            protocol_id="",  # FIXME
            assay_id="",  # FIXME
        )


@dataclass
class Instrument:
    serial_number: str
    nickname: str

    @staticmethod
    def create(reader: CsvReader) -> Instrument:
        reader.pop_csv_block()
        return Instrument(serial_number="", nickname="")  # FIXME


@dataclass
class Plate:
    number: str

    @staticmethod
    def create(reader: CsvReader) -> list[Plate]:
        reader.pop_csv_block()
        plates: list[Plate] = []  # FIXME
        return plates


@dataclass
class Data:
    plates: list[Plate]
    number_of_wells: Optional[float]
    basic_assay_info: BasicAssayInfo
    instrument: Instrument

    @staticmethod
    def create(reader: CsvReader) -> Data:
        data = reader.pop_csv_block()
        rows, cols = data.shape

        return Data(
            plates=Plate.create(reader),
            number_of_wells=(rows - 4) * (cols - 1),
            basic_assay_info=BasicAssayInfo.create(reader),
            instrument=Instrument.create(reader),
        )
