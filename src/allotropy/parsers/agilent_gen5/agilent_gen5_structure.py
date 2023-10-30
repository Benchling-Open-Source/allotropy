from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.agilent_gen5.absorbance_plate_data import AbsorbancePlateData
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.fluorescence_plate_data import FluorescencePlateData
from allotropy.parsers.agilent_gen5.luminescence_plate_data import LuminescencePlateData
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import assert_not_none


@dataclass
class Data:
    plates: list[PlateData]

    @staticmethod
    def create_plate_data(
        software_version_chunk: Optional[str],
        file_paths_chunk: Optional[str],
        all_data_chunk: Optional[str],
    ) -> PlateData:
        software_version_chunk = assert_not_none(
            software_version_chunk, "software_version_chunk"
        )
        file_paths_chunk = assert_not_none(file_paths_chunk, "file_paths_chunk")
        all_data_chunk = assert_not_none(all_data_chunk, "all_data_chunk")

        all_data_sections = all_data_chunk.split("\n\n")
        for data_section in all_data_sections:
            if data_section.startswith("Plate Type"):
                if ReadMode.ABSORBANCE.value in data_section:
                    return AbsorbancePlateData(
                        software_version_chunk, file_paths_chunk, all_data_chunk
                    )
                elif ReadMode.FLUORESCENCE.value in data_section:
                    return FluorescencePlateData(
                        software_version_chunk, file_paths_chunk, all_data_chunk
                    )
                elif ReadMode.LUMINESCENCE.value in data_section:
                    return LuminescencePlateData(
                        software_version_chunk, file_paths_chunk, all_data_chunk
                    )
        msg = "Read mode not found"
        raise AllotropeConversionError(msg)

    @staticmethod
    def create(lines_reader: LinesReader) -> Data:
        plates: list[PlateData] = []
        software_version_chunk = None
        file_paths_chunk = None
        all_data_chunk = None

        plate_chunks = lines_reader.contents.strip().split(4 * "\n")
        completed_plate = False
        for plate_chunk in plate_chunks:
            if plate_chunk.startswith("Software Version"):
                if completed_plate:
                    new_plate = Data.create_plate_data(
                        software_version_chunk, file_paths_chunk, all_data_chunk
                    )
                    plates.append(new_plate)
                    completed_plate = False
                software_version_chunk = plate_chunk
            elif plate_chunk.startswith("Experiment File Path"):
                file_paths_chunk = plate_chunk
            elif plate_chunk.startswith("Plate Number"):
                all_data_chunk = plate_chunk
                completed_plate = True
            elif plate_chunk.startswith("Actual Temperature"):
                all_data_chunk = f"{all_data_chunk}\n\n{plate_chunk}"

        if completed_plate:
            new_plate = Data.create_plate_data(
                software_version_chunk, file_paths_chunk, all_data_chunk
            )
            plates.append(new_plate)

        if not plates:
            msg = "No plate data found in file"
            raise AllotropeConversionError(msg)

        return Data(plates)
