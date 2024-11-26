from re import search

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
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
from allotropy.parsers.cytiva_unicorn.utils import (
    min_to_sec,
    parse_data_cube_bynary,
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
    def create_data_cube(
        cls,
        handler: UnicornZipHandler,
        curve_element: StrictElement,
        data_cuve_component: DataCubeComponent,
    ) -> DataCube:
        data_name = curve_element.recursive_find(
            ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
        ).get_text()
        data_handler = handler.get_content_from_pattern(data_name)

        return DataCube(
            label=curve_element.find("Name").get_text(),
            structure_dimensions=[
                DataCubeComponent(
                    type_=FieldComponentDatatype.float,
                    concept="retention time",
                    unit="s",
                ),
            ],
            structure_measures=[data_cuve_component],
            dimensions=[
                min_to_sec(
                    parse_data_cube_bynary(
                        data_handler.get_file_from_pattern("CoordinateData.Volumes$")
                    )
                )
            ],
            measures=[
                parse_data_cube_bynary(
                    data_handler.get_file_from_pattern("CoordinateData.Amplitudes$")
                )
            ],
        )
