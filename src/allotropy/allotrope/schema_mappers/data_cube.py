from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
    TDimensionArray,
    TFunction,
    TMeasureArray,
)
from allotropy.exceptions import AllotropeConversionError


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
    dimensions: Sequence[Sequence[float] | Sequence[str] | Sequence[bool]]
    measures: Sequence[
        Sequence[float | None] | Sequence[str | None] | Sequence[bool | None]
    ]


class DataCubeProtocol(Protocol):
    def __init__(
        self,
        label: str,
        cube_structure: TDatacubeStructure,
        data: TDatacubeData,
    ):
        pass


DataCubeType = TypeVar("DataCubeType", bound=DataCubeProtocol)


T = TypeVar("T", bound=float | str | bool)


def _is_type(type_: type[T], value: float | str | int) -> bool:
    return isinstance(value, type_) or type_ is float and isinstance(value, int)


def _get_typed_dimension(
    type_: type[T], values: Sequence[float | str | bool]
) -> list[T] | None:
    # Allow ints or floats for float list.
    result: list[T] = [
        # Typing is not smart enough to tell that calling type_(value) results in a value of type: type_,
        # which I just can't deal with.
        type_(value)  # type: ignore[misc]
        for value in values
        if _is_type(type_, value)
    ]
    return result if len(result) == len(values) else None


def _get_dimensions(
    dimensions: Sequence[Sequence[float] | Sequence[str] | Sequence[bool]],
) -> list[TDimensionArray | TFunction]:
    result: list[TDimensionArray | TFunction] = []
    for dimension in dimensions:
        float_list = _get_typed_dimension(float, dimension)
        str_list = _get_typed_dimension(str, dimension)
        bool_list = _get_typed_dimension(bool, dimension)
        # NOTE: given the input types, this should be impossible, however, typing does not believe this, so we
        # add this check. This allows us to safely put "or []" at the end of result.append, confident that all
        # 3 lists are only falsy if the input is empty.
        if float_list is None and str_list is None and bool_list is None:
            msg = f"Unable to extract a TDimensionArray from datacube dimension: {dimension}"
            raise AllotropeConversionError(msg)
        result.append(float_list or str_list or bool_list or [])
    return result


def _get_typed_measure(
    type_: type[T], values: Sequence[float | str | bool | None]
) -> list[T | None] | None:
    result: list[T | None] = [
        # Typing is not smart enough to tell that calling type_(value) results in a value of type: type_,
        # which I just can't deal with.
        None if value is None else type_(value)  # type: ignore[misc]
        for value in values
        if value is None or _is_type(type_, value)
    ]
    return result if len(result) == len(values) else None


def _get_measures(
    measures: Sequence[
        Sequence[float | None] | Sequence[str | None] | Sequence[bool | None]
    ],
) -> list[TMeasureArray]:
    result: list[TMeasureArray] = []
    for measure in measures:
        float_list = _get_typed_measure(float, measure)
        str_list = _get_typed_measure(str, measure)
        bool_list = _get_typed_measure(bool, measure)
        # NOTE: given the input types, this should be impossible, however, typing does not believe us, so we
        # add
        # this check. This allows us to safely put "or []" at the end of result.append, confident that all
        # 3 lists are only falsy if the input is empty.
        if float_list is None and str_list is None and bool_list is None:
            msg = f"Unable to extract a TMeasureArray from datacube measure: {measure}"
            raise AllotropeConversionError(msg)
        result.append(float_list or str_list or bool_list or [])
    return result


def get_data_cube(
    data_cube: DataCube | None, data_cube_class: type[DataCubeType]
) -> DataCubeType | None:
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
            dimensions=_get_dimensions(data_cube.dimensions),
            measures=_get_measures(data_cube.measures),
        ),
    )
