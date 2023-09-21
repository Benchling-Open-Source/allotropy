from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

TTupleData = list[Optional[Union[float, bool, str]]]


TUnit = str


TBooleanArray = list[bool]


TBooleanOrNullArray = list[Optional[bool]]


TNumberArray = list[float]


TNumberOrNullArray = list[Optional[float]]


TStringArray = list[str]


TStringOrNullArray = list[Optional[str]]


TClass = str


@dataclass
class TStringValueItem:
    value: str
    field_type: str


TStringValue = Union[str, TStringValueItem]


@dataclass
class TDateTimeValueItem:
    field_type: TClass
    value: str


TDateTimeValue = Union[str, TDateTimeValueItem]


@dataclass
class TBooleanValueItem:
    field_type: TClass
    value: bool


TBooleanValue = Union[bool, TBooleanValueItem]


class TStatisticDatumRole(Enum):
    arithmetic_mean_role = "arithmetic mean role"
    median_role = "median role"
    relative_standard_deviation_role = "relative standard deviation role"
    skewness_role = "skewness role"
    standard_deviation_role = "standard deviation role"
    variance_role = "variance role"
    maximum_value_role = "maximum value role"
    minimum_value_role = "minimum value role"


@dataclass
class TQuantityValue:
    value: float
    unit: TUnit
    has_statistic_datum_role: Optional[TStatisticDatumRole] = None
    field_type: Optional[TClass] = None


@dataclass
class TNullableQuantityValue:
    value: Optional[float]
    unit: TUnit
    has_statistic_datum_role: Optional[TStatisticDatumRole] = None
    field_type: Optional[TClass] = None


# NOTE: this is defined to allow override of unit default for TQuaniityValue<Unit> (otherwise mypy gets mad)
@dataclass
class TQuantityValueWithOptionalUnit:
    value: float
    unit: Optional[TUnit]
    has_statistic_datum_role: Optional[TStatisticDatumRole] = None
    field_type: Optional[TClass] = None


@dataclass
class TNullableQuantityValueWithOptionalUnit:
    value: Optional[float]
    unit: Optional[TUnit]
    has_statistic_datum_role: Optional[TStatisticDatumRole] = None
    field_type: Optional[TClass] = None


class FieldComponentDatatype(Enum):
    double = "double"
    float = "float"  # noqa: A003
    decimal = "decimal"
    integer = "integer"
    byte = "byte"
    int = "int"  # noqa: A003
    short = "short"
    long = "long"
    string = "string"
    boolean = "boolean"
    dateTime = "dateTime"


class Scale(Enum):
    nominal = "nominal"
    ordinal = "ordinal"
    cardinal = "cardinal"
    interval = "interval"
    range = "range"  # noqa: A003


class Type(Enum):
    linear = "linear"
    logarithmic = "logarithmic"


@dataclass
class TFunction:
    type: Optional[Type] = Type.linear  # noqa: A003
    start: Optional[float] = 1
    length: Optional[float] = None
    incr: Optional[float] = 1


@dataclass
class TDatacubeComponent:
    field_componentDatatype: FieldComponentDatatype
    concept: TClass
    unit: Optional[TUnit] = None
    scale: Optional[Scale] = None
    field_asm_fill_value: Optional[Union[str, float, int, bool]] = None


TDimensionArray = Union[TNumberArray, TBooleanArray, TStringArray]


TMeasureArray = Union[TNumberOrNullArray, TBooleanOrNullArray, TStringOrNullArray]


@dataclass
class TDatacubeStructure:
    dimensions: list[TDatacubeComponent]
    measures: list[TDatacubeComponent]


"""
TODO: datamodel-codegen cannot properly generate the models for TDatacubeData with the
oneOf{measures, points} constraint. I can't figure out how to do it correctly right now either.
We need to either figure this out and file a bug with datamodel-codegen or fix the schema.

@dataclass
class TDimensionData:
    dimensions: List[Union[TDimensionArray, TFunction]]


@dataclass
class TMeasureDatum:
    measures: List[TMeasureArray]


@dataclass
class TMeasureDatum1:
    points: List[TTupleData]


TMeasureData = Union[TMeasureDatum, TMeasureDatum1]


@dataclass
class TDatacubeData(TDimensionData):
    pass
"""


@dataclass
class TDatacubeData:
    dimensions: list[Union[TDimensionArray, TFunction]]
    measures: Optional[list[TMeasureArray]] = None
    points: Optional[list[TTupleData]] = None

    def __post_init__(self) -> None:
        # Logic for enforcing oneOf
        if not (self.measures is None) ^ (self.points is None):
            error = "Exactly one of measures or points must be set"
            raise ValueError(error)


@dataclass
class TDatacube:
    label: Optional[str] = None
    cube_structure: Optional[TDatacubeStructure] = None
    data: Optional[TDatacubeData] = None
