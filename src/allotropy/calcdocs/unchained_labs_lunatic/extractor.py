from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)
from allotropy.calcdocs.extractor import Element, Extractor


class LunaticExtractor(Extractor[Measurement]):
    @classmethod
    def to_element(cls, measurement: Measurement) -> Element:
        custom_info = (
            measurement.calc_docs_custom_info
            if measurement.calc_docs_custom_info
            else {}
        )

        return Element(
            uuid=measurement.identifier,
            data={
                "uuid": measurement.identifier,
                "wavelength id": measurement.wavelength_identifier,
                "absorbance": measurement.absorbance,
                **custom_info,
            },
        )
