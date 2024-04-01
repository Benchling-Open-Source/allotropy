from __future__ import annotations

from dataclasses import dataclass

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_gen5.constants import MULTIPLATE_FILE_ERROR
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader


@dataclass(frozen=True)
class Data:
    plate_data: PlateData

    @staticmethod
    def create(section_lines_reader: SectionLinesReader) -> Data:
        plates = list(section_lines_reader.iter_sections("^Software Version"))

        if not plates:
            msg = "No plate data found in file."
            raise AllotropeConversionError(msg)

        if len(plates) > 1:
            raise AllotropeConversionError(MULTIPLATE_FILE_ERROR)

        return Data(PlateData.create(plates[0]))
