from __future__ import annotations

from dataclasses import dataclass

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.plate_data import (
    AbsorbancePlateData,
    FluorescencePlateData,
    LuminescencePlateData,
    PlateData,
)
from allotropy.parsers.agilent_gen5.section_reader import SectionLinesReader
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none


@dataclass
class Data:
    plates: list[PlateData]

    @staticmethod
    def create_plate_data(lines_reader: LinesReader) -> PlateData:
        software_version_chunk = assert_not_none(
            lines_reader.drop_until("^Software Version"), "Software Version"
        )

        assert_not_none(
            lines_reader.drop_until("^Experiment File Path"), "Experiment File Path"
        )
        file_paths_chunk = "\n".join(lines_reader.pop_until_empty())

        assert_not_none(
            lines_reader.drop_until("^Plate Number"),
            "Plate Number",
        )
        all_data_chunk = "\n".join(lines_reader.pop_until("^Software Version"))

        all_data_sections = all_data_chunk.split("\n\n")
        for data_section in all_data_sections:
            if data_section.startswith("Plate Type"):
                if ReadMode.ABSORBANCE.value in data_section:
                    return PlateData.create(
                        AbsorbancePlateData,
                        software_version_chunk,
                        file_paths_chunk,
                        all_data_chunk,
                    )
                elif ReadMode.FLUORESCENCE.value in data_section:
                    return PlateData.create(
                        FluorescencePlateData,
                        software_version_chunk,
                        file_paths_chunk,
                        all_data_chunk,
                    )
                elif ReadMode.LUMINESCENCE.value in data_section:
                    return PlateData.create(
                        LuminescencePlateData,
                        software_version_chunk,
                        file_paths_chunk,
                        all_data_chunk,
                    )
        msg = "Read mode not found"
        raise AllotropeConversionError(msg)

    @staticmethod
    def create(section_lines_reader: SectionLinesReader) -> Data:
        plates: list[PlateData] = [
            Data.create_plate_data(lines_reader)
            for lines_reader in section_lines_reader.iter_sections("^Software Version")
        ]

        if not plates:
            msg = "No plate data found in file"
            raise AllotropeConversionError(msg)

        return Data(plates)
