from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.bmg_labtech_smart_control.calculated_data_structure import (
    CalculatedDataStructure,
)


class BmgLabtechSmartControlExtractor(Extractor[CalculatedDataStructure]):
    @classmethod
    def to_element(cls, calc_data_struct: CalculatedDataStructure) -> Element:
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
