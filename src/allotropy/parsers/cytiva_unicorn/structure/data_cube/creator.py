from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
)
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.reader import (
    DataCubeReader,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    Min2Sec,
    Transformation,
)


def create_data_cube(
    handler: UnicornZipHandler,
    curve_element: StrictElement,
    data_cube_component: DataCubeComponent,
    transformation: Transformation | None = None,
) -> DataCube:
    names = ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
    data_name = curve_element.recursive_find(names).get_text()
    data_cube_zip_handler = handler.get_zip_from_pattern(data_name)

    return DataCube(
        label=curve_element.find("Name").get_text(),
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="s",
            ),
        ],
        structure_measures=[data_cube_component],
        dimensions=[
            DataCubeReader(
                handler=data_cube_zip_handler,
                name="Volumes",
                transformation=Min2Sec(),
            ).get_data()
        ],
        measures=[
            DataCubeReader(
                handler=data_cube_zip_handler,
                name="Amplitudes",
                transformation=transformation,
            ).get_data()
        ],
    )
