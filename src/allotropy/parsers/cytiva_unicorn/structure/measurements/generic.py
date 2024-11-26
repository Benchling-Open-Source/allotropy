from re import search

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Measurement,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)


class UnicornMeasurement(Measurement):
    @classmethod
    def filter_curve(
        cls, curve_elements: list[StrictElement], pattern: str
    ) -> StrictElement:
        for element in curve_elements:
            if search(pattern, element.find("Name").get_text()):
                return element
        msg = f"Unable to find curve element with pattern {pattern}"
        raise AllotropeConversionError(msg)
