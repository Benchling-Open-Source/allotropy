from dataclasses import dataclass
from typing import Protocol, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)


@dataclass(frozen=True)
class DataCubeComponent:
    type_: FieldComponentDatatype
    concept: str
    unit: str


@dataclass(frozen=True)
class DataCube:
    label: str
    structure_dimensions: list[DataCubeComponent]
    structure_measures: list[DataCubeComponent]
    dimensions: list[tuple[float, ...]]
    measures: list[tuple[float | None, ...]]


class DataCubeProtocol(Protocol):
    def __init__(
        self,
        label: str,
        cube_structure: TDatacubeStructure,
        data: TDatacubeData,
    ):
        pass


DataCubeType = TypeVar("DataCubeType", bound=DataCubeProtocol)


def get_data_cube(data_cube: DataCube | None, data_cube_class: type[DataCubeType]) -> DataCubeType | None:
    if data_cube is None:
        return None
    return data_cube_class(
        label=data_cube.label,
        cube_structure=TDatacubeStructure(
            dimensions=[
                TDatacubeComponent(
                    field_componentDatatype=structure_dim.type_,
                    concept=structure_dim.concept,
                    unit=structure_dim.unit,
                )
                for structure_dim in data_cube.structure_dimensions
            ],
            measures=[
                TDatacubeComponent(
                    field_componentDatatype=structure_dim.type_,
                    concept=structure_dim.concept,
                    unit=structure_dim.unit,
                )
                for structure_dim in data_cube.structure_measures
            ],
        ),
        data=TDatacubeData(
            dimensions=[list(dim) for dim in data_cube.dimensions],
            measures=[list(dim) for dim in data_cube.measures],
        ),
    )
