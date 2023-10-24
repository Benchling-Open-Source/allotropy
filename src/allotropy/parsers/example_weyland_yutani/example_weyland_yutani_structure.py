from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from allotropy.parsers.lines_reader import CsvReader


@dataclass
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: Optional[str]

    @staticmethod
    def create(reader: CsvReader) -> BasicAssayInfo:
        old_line_num = reader.current_line
        list(reader.pop_until("^Checksum"))
        line = reader.pop()
        checksum = None
        if line:
            checksum = line.split(",")[1]
        reader.current_line = old_line_num
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
class Plate:
    number: str

    @staticmethod
    def create() -> list[Plate]:
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
        return Data(
            plates=Plate.create(reader),
            number_of_wells=0,
            basic_assay_info=BasicAssayInfo.create(reader),
            instrument=Instrument.create(reader),
        )
