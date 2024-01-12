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
    MicrogramPerMicroliter,
    MicrogramPerMilliliter,
    Microliter,
    Micrometer,
    MilliAbsorbanceUnit,
    MilligramPerMilliliter,
    Millimeter,
    MillimeterOfMercury,
    MillimolePerLiter,
    MillionCellsPerMilliliter,
    MilliOsmolesPerKilogram,
    MilliSecond,
    NanogramPerMicroliter,
    NanogramPerMilliliter,
    Nanometer,
    Number,
    NumberPerMicroliter,
    OpticalDensity,
    Percent,
    PH,
    PicogramPerMilliliter,
    RelativeFluorescenceUnit,
    RelativeLightUnit,
    SecondTime,
    SquareCentimetersPerGram,
    TODO,
    Unitless,
    UnitPerLiter,
)


@dataclass
class TQuantityValueCentimeter(TQuantityValueWithOptionalUnit, Centimeter):
    pass


@dataclass
class TQuantityValueMillimeter(TQuantityValueWithOptionalUnit, Millimeter):
    pass


@dataclass
class TQuantityValueNanometer(TQuantityValueWithOptionalUnit, Nanometer):
    pass


@dataclass
class TQuantityValueMicrometer(TQuantityValueWithOptionalUnit, Micrometer):
    pass


@dataclass
class TQuantityValueHertz(TQuantityValueWithOptionalUnit, Hertz):
    pass


@dataclass
class TQuantityValueCubicMillimeter(TQuantityValueWithOptionalUnit, CubicMillimeter):
    pass


@dataclass
class TQuantityValueUnitless(TQuantityValueWithOptionalUnit, Unitless):
    pass


@dataclass
class TQuantityValueSecondTime(TQuantityValueWithOptionalUnit, SecondTime):
    pass


@dataclass
class TQuantityValuePercent(TQuantityValueWithOptionalUnit, Percent):
    pass


@dataclass
class TQuantityValueCell(TQuantityValueWithOptionalUnit, Cell):
    pass


@dataclass
class TQuantityValueMicroliter(TQuantityValueWithOptionalUnit, Microliter):
    pass


@dataclass
class TQuantityValueNumberPerMicroliter(
    TQuantityValueWithOptionalUnit, NumberPerMicroliter
):
    pass


@dataclass
class TQuantityValueMilliSecond(TQuantityValueWithOptionalUnit, MilliSecond):
    pass


@dataclass
class TQuantityValueMillionCellsPerMilliliter(
    TQuantityValueWithOptionalUnit, MillionCellsPerMilliliter
):
    pass


@dataclass
class TQuantityValueTODO(TQuantityValueWithOptionalUnit, TODO):
    pass


@dataclass
class TQuantityValueGramPerLiter(TQuantityValueWithOptionalUnit, GramPerLiter):
    pass


@dataclass
class TQuantityValueDegreeCelsius(TQuantityValueWithOptionalUnit, DegreeCelsius):
    pass


@dataclass
class TQuantityValueNumber(TQuantityValueWithOptionalUnit, Number):
    pass


@dataclass
class TQuantityValueNanogramPerMicroliter(
    NanogramPerMicroliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueMicrogramPerMicroliter(
    TQuantityValueWithOptionalUnit, MicrogramPerMicroliter
):
    pass


@dataclass
class TQuantityValuePicogramPerMilliliter(
    TQuantityValueWithOptionalUnit, PicogramPerMilliliter
):
    pass


@dataclass
class TQuantityValueNanogramPerMilliliter(
    TQuantityValueWithOptionalUnit, NanogramPerMilliliter
):
    pass


@dataclass
class TQuantityValueMicrogramPerMilliliter(
    TQuantityValueWithOptionalUnit, MicrogramPerMilliliter
):
    pass


@dataclass
class TQuantityValueMilligramPerMilliliter(
    TQuantityValueWithOptionalUnit, MilligramPerMilliliter
):
    pass


@dataclass
class TQuantityValueUnitPerLiter(TQuantityValueWithOptionalUnit, UnitPerLiter):
    pass


@dataclass
class TQuantityValueMillimeterOfMercury(
    TQuantityValueWithOptionalUnit, MillimeterOfMercury
):
    pass


@dataclass
class TQuantityValueOpticalDensity(TQuantityValueWithOptionalUnit, OpticalDensity):
    pass


@dataclass
class TQuantityValuePH(TQuantityValueWithOptionalUnit, PH):
    pass


@dataclass
class TQuantityValueMilliOsmolesPerKilogram(
    TQuantityValueWithOptionalUnit, MilliOsmolesPerKilogram
):
    pass


@dataclass
class TQuantityValueMillimolePerLiter(
    TQuantityValueWithOptionalUnit, MillimolePerLiter
):
    pass


@dataclass
class TQuantityValueMilliAbsorbanceUnit(
    TQuantityValueWithOptionalUnit, MilliAbsorbanceUnit
):
    pass


@dataclass
class TRelativeFluorescenceUnit(
    TQuantityValueWithOptionalUnit, RelativeFluorescenceUnit
):
    pass


@dataclass
class TRelativeLightUnit(TQuantityValueWithOptionalUnit, RelativeLightUnit):
    pass


@dataclass
class TQuantityValueSquareCentimetersPerGram(
    TQuantityValueWithOptionalUnit, SquareCentimetersPerGram
):
    pass


@dataclass
class TNullableQuantityValueCell(TNullableQuantityValueWithOptionalUnit, Cell):
    pass


@dataclass
class TNullableQuantityValueGramPerLiter(
    TNullableQuantityValueWithOptionalUnit, GramPerLiter
):
    pass


@dataclass
class TNullableQuantityValueMicrometer(
    TNullableQuantityValueWithOptionalUnit, Micrometer
):
    pass


@dataclass
class TNullableQuantityValueMilliOsmolesPerKilogram(
    TNullableQuantityValueWithOptionalUnit, MilliOsmolesPerKilogram
):
    pass


@dataclass
class TNullableQuantityValueMillimeterOfMercury(
    TNullableQuantityValueWithOptionalUnit, MillimeterOfMercury
):
    pass


@dataclass
class TNullableQuantityValueMillimolePerLiter(
    TNullableQuantityValueWithOptionalUnit, MillimolePerLiter
):
    pass


@dataclass
class TNullableQuantityValueMillionCellsPerMilliliter(
    TNullableQuantityValueWithOptionalUnit, MillionCellsPerMilliliter
):
    pass


@dataclass
class TNullableQuantityValueOpticalDensity(
    TNullableQuantityValueWithOptionalUnit, OpticalDensity
):
    pass


@dataclass
class TNullableQuantityValuePH(TNullableQuantityValueWithOptionalUnit, PH):
    pass


@dataclass
class TNullableQuantityValuePercent(TNullableQuantityValueWithOptionalUnit, Percent):
    pass


@dataclass
class TNullableQuantityValueTODO(TNullableQuantityValueWithOptionalUnit, TODO):
    pass


@dataclass
class TNullableQuantityValueUnitPerLiter(
    TNullableQuantityValueWithOptionalUnit, UnitPerLiter
):
    pass


@dataclass
class TNullableQuantityValueUnitless(TNullableQuantityValueWithOptionalUnit, Unitless):
    pass
