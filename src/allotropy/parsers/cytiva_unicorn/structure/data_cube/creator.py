from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.reader import (
    DataCubeReader,
)
from allotropy.parsers.cytiva_unicorn.structure.data_cube.transformations import (
    Transformation,
)


def create_data_cube(
    handler: UnicornZipHandler,
    label: str,
    data_cube_component: DataCubeComponent,
    transformation: Transformation | None,
) -> DataCube:
    return DataCube(
        label=label,
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention volume",
                unit="mL",
            ),
        ],
        structure_measures=[data_cube_component],
        dimensions=[
            list(
                DataCubeReader(
                    handler=handler,
                    name="Volumes",
                ).get_data()
            )
        ],
        measures=[
            list(
                DataCubeReader(
                    handler=handler,
                    name="Amplitudes",
                    transformation=transformation,
                ).get_data()
            )
        ],
    )
