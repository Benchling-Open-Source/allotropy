from dataclasses import dataclass

from allotropy.allotrope.models.shared.definitions.definitions import (
    TNullableQuantityValueWithOptionalUnit,
    TQuantityValueWithOptionalUnit,
)
from allotropy.allotrope.models.shared.definitions.units import (
    Cell,
    Centimeter,
    CubicMillimeter,
    DegreeCelsius,
    GramPerLiter,
    Hertz,
    Microliter,
    Micrometer,
    Millimeter,
    MillimeterOfMercury,
    MillimolePerLiter,
    MillionCellsPerMilliliter,
    MilliOsmolesPerKilogram,
    MilliSecond,
    Nanometer,
    Number,
    OpticalDensity,
    Percent,
    PH,
    PicogramPerMilliliter,
    SecondTime,
    TODO,
    Unitless,
    UnitPerLiter,
)


@dataclass
class TQuantityValueCentimeter(Centimeter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMillimeter(Millimeter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueNanometer(Nanometer, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMicrometer(Micrometer, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueHertz(Hertz, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueCubicMillimeter(CubicMillimeter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueUnitless(Unitless, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueSecondTime(SecondTime, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValuePercent(Percent, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueCell(Cell, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMicroliter(Microliter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMilliSecond(MilliSecond, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMillionCellsPerMilliliter(
    MillionCellsPerMilliliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueTODO(TODO, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueGramPerLiter(GramPerLiter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueDegreeCelsius(DegreeCelsius, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueNumber(Number, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValuePicogramPerMilliliter(
    PicogramPerMilliliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueUnitPerLiter(UnitPerLiter, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMillimeterOfMercury(
    MillimeterOfMercury, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueOpticalDensity(OpticalDensity, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValuePH(PH, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueMilliOsmolesPerKilogram(
    MilliOsmolesPerKilogram, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueMillimolePerLiter(
    MillimolePerLiter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueCell(Cell, TNullableQuantityValueWithOptionalUnit):
    pass


@dataclass
class TNullableQuantityValueGramPerLiter(
    GramPerLiter, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueMicrometer(
    Micrometer, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueMilliOsmolesPerKilogram(
    MilliOsmolesPerKilogram, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueMillimeterOfMercury(
    MillimeterOfMercury, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueMillimolePerLiter(
    MillimolePerLiter, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueMillionCellsPerMilliliter(
    MillionCellsPerMilliliter, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueOpticalDensity(
    OpticalDensity, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValuePH(PH, TNullableQuantityValueWithOptionalUnit):
    pass


@dataclass
class TNullableQuantityValuePercent(Percent, TNullableQuantityValueWithOptionalUnit):
    pass


@dataclass
class TNullableQuantityValueTODO(TODO, TNullableQuantityValueWithOptionalUnit):
    pass


@dataclass
class TNullableQuantityValueUnitPerLiter(
    UnitPerLiter, TNullableQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueUnitless(Unitless, TNullableQuantityValueWithOptionalUnit):
    pass
