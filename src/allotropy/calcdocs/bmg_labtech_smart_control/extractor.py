from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)
from allotropy.calcdocs.extractor import Element, Extractor


@dataclass
class CalculatedDataMeasurementStructure:
    measurement: Measurement
    average_of_blank_used: float | None
    corrected_value: float | None


class BmgLabtechSmartControlExtractor(Extractor[CalculatedDataMeasurementStructure]):
    @classmethod
    def to_element(
        cls, calc_data_struct: CalculatedDataMeasurementStructure
    ) -> Element:
        measurement = calc_data_struct.measurement
        return Element(
            uuid=calc_data_struct.measurement.identifier,
            data={
                "uuid": calc_data_struct.measurement.identifier,
                "measurement": calc_data_struct.measurement.fluorescence,
                "sample_role_type": measurement.sample_role_type.name
                if measurement.sample_role_type
                else None,
                "corrected_value": calc_data_struct.corrected_value
                if calc_data_struct.corrected_value
                else None,
                "average_of_blank_used": calc_data_struct.average_of_blank_used,
                "fluorescence": measurement.fluorescence
                if measurement.fluorescence
                else None,
            },
        )
