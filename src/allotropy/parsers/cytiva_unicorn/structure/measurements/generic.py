from re import search

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
    Measurement,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.creator import (
    create_data_cube,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    Transformation,
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

    @classmethod
    def get_data_cube_handler(
        cls, handler: UnicornZipHandler, curve_element: StrictElement
    ) -> UnicornZipHandler:
        names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
        data_name = curve_element.recursive_find(names).get_text()
        return handler.get_zip_from_pattern(data_name)

    @classmethod
    def get_data_cube(
        cls,
        handler: UnicornZipHandler,
        curve: StrictElement,
        data_cube_component: DataCubeComponent,
        transformation: Transformation | None = None,
    ) -> DataCube:
        return create_data_cube(
            cls.get_data_cube_handler(handler, curve),
            curve.find("Name").get_text(),
            data_cube_component,
            transformation,
        )
