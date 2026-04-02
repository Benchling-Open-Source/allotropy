from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

import numpy as np

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
) -> Sequence[T] | None:
    # Optimize for numpy arrays: keep as numpy array to save memory
    # numpy arrays use ~4 bytes/float vs ~28 bytes for Python float objects
    # Conversion to list happens during JSON serialization
    if isinstance(values, np.ndarray):
        # For float arrays, return the numpy array directly
        if type_ is float and values.dtype in (
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ):
            return values
        elif type_ is str and values.dtype.kind in (
            "U",
            "S",
            "O",
        ):  # Unicode, bytes, object
            return values
        elif type_ is bool and values.dtype == np.bool_:
            return values

    # Fallback to original logic for non-numpy sequences
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
        # add this check.
        if float_list is None and str_list is None and bool_list is None:
            msg = f"Unable to extract a TDimensionArray from datacube dimension: {dimension}"
            raise AllotropeConversionError(msg)
        # Use explicit None checks to handle numpy arrays (which can't be used with 'or')
        # At least one of these is not None (checked above), so no need for '[] fallback
        typed_dim = (
            float_list
            if float_list is not None
            else (str_list if str_list is not None else bool_list)
        )
        result.append(typed_dim)  # type: ignore[arg-type]
    return result


def _get_typed_measure(
    type_: type[T], values: Sequence[float | str | bool | None]
) -> Sequence[T | None] | None:
    # Optimize for numpy arrays: keep as numpy array to save memory
    # numpy arrays use ~4 bytes/float vs ~28 bytes for Python float objects
    # Conversion to list happens during JSON serialization
    if isinstance(values, np.ndarray):
        # For float arrays, return the numpy array directly
        if type_ is float and values.dtype in (
            np.float32,
            np.float64,
            np.int32,
            np.int64,
        ):
            return values
        elif type_ is str and values.dtype.kind in ("U", "S", "O"):
            return values
        elif type_ is bool and values.dtype == np.bool_:
            return values

    # Fallback to original logic for non-numpy sequences
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
        # NOTE: given the input types, this should be impossible, however, typing does not believe us, so we add
        # this check.
        if float_list is None and str_list is None and bool_list is None:
            msg = f"Unable to extract a TMeasureArray from datacube measure: {measure}"
            raise AllotropeConversionError(msg)
        # Use explicit None checks to handle numpy arrays (which can't be used with 'or')
        # At least one of these is not None (checked above), so no need for [] fallback
        typed_measure = (
            float_list
            if float_list is not None
            else (str_list if str_list is not None else bool_list)
        )
        result.append(typed_measure)  # type: ignore[arg-type]
    return result


def _convert_to_list(
    sequence: Sequence[T] | Sequence[T | None],
) -> list[T] | list[T | None]:
    """Convert numpy arrays to Python lists for JSON serialization."""
    if isinstance(sequence, np.ndarray):
        return sequence.tolist()
    return list(sequence) if not isinstance(sequence, list) else sequence


def get_data_cube(
    data_cube: DataCube | None, data_cube_class: type[DataCubeType]
) -> DataCubeType | None:
    if data_cube is None:
        return None

    # Get dimensions and measures (may contain numpy arrays for memory efficiency)
    dimensions = _get_dimensions(data_cube.dimensions)
    measures = _get_measures(data_cube.measures)

    # Convert numpy arrays to lists right before pydantic serialization
    # This is the last moment conversion to minimize memory usage
    dimensions_as_lists = [_convert_to_list(dim) for dim in dimensions]  # type: ignore[arg-type]
    measures_as_lists = [_convert_to_list(measure) for measure in measures]

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
            dimensions=dimensions_as_lists,  # type: ignore[arg-type]
            measures=measures_as_lists,  # type: ignore[arg-type]
        ),
    )
