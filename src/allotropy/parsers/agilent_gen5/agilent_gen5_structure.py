from __future__ import annotations

from dataclasses import dataclass

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader


@dataclass(frozen=True)
class Data:
    plates: list[PlateData]

    @staticmethod
    def create(section_lines_reader: SectionLinesReader) -> Data:
        plates: list[PlateData] = [
            PlateData.create(lines_reader)
            for lines_reader in section_lines_reader.iter_sections("^Software Version")
        ]

        if not plates:
            msg = "No plate data found in file."
            raise AllotropeConversionError(msg)

        return Data(plates)
