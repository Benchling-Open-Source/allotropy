from __future__ import annotations

from dataclasses import dataclass

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.agilent_gen5.create_plate_data import create_plate_data
from allotropy.parsers.agilent_gen5.plate_data import PlateData
from allotropy.parsers.lines_reader import LinesReader


@dataclass
class Data:
    plates: list[PlateData]

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
                    new_plate = create_plate_data(
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
            new_plate = create_plate_data(
                software_version_chunk, file_paths_chunk, all_data_chunk
            )
            plates.append(new_plate)

        if not plates:
            msg = "No plate data found in file"
            raise AllotropeConversionError(msg)

        return Data(plates)
