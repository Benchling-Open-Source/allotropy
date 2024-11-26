from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
    Measurement,
)
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
)
from allotropy.parsers.cytiva_unicorn.utils import (
    min_to_sec,
    parse_data_cube_bynary,
)


class UnicornMeasurement(Measurement):
    @classmethod
    def create_data_cube(
        cls,
        handler: UnicornFileHandler,
        curve_element: StrictElement,
        data_cuve_component: DataCubeComponent,
    ) -> DataCube:
        data_name = curve_element.find_text(
            ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
        )
        data_handler = handler.get_content_from_pattern(data_name)

        return DataCube(
            label=curve_element.find_text(["Name"]),
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
