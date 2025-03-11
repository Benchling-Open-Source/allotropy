from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)


@dataclass
class CalculatedDataStructure:
    measurement: Measurement
    average_of_blank_used: float | None
    corrected_value: float | None
