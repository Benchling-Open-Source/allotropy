from dataclasses import dataclass

from allotropy.allotrope.models.shared.definitions.definitions import (
    TNullableQuantityValue,
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
class TQuantityValueNumberPerMicroliter(
    NumberPerMicroliter, TQuantityValueWithOptionalUnit
):
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
class TQuantityValueNanogramPerMicroliter(
    NanogramPerMicroliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueMicrogramPerMicroliter(
    MicrogramPerMicroliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValuePicogramPerMilliliter(
    PicogramPerMilliliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueNanogramPerMilliliter(
    NanogramPerMilliliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueMicrogramPerMilliliter(
    MicrogramPerMilliliter, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TQuantityValueMilligramPerMilliliter(
    MilligramPerMilliliter, TQuantityValueWithOptionalUnit
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
class TQuantityValueMilliAbsorbanceUnit(
    MilliAbsorbanceUnit, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TRelativeFluorescenceUnit(
    RelativeFluorescenceUnit, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TRelativeLightUnit(RelativeLightUnit, TQuantityValueWithOptionalUnit):
    pass


@dataclass
class TQuantityValueSquareCentimetersPerGram(
    SquareCentimetersPerGram, TQuantityValueWithOptionalUnit
):
    pass


@dataclass
class TNullableQuantityValueCell(Cell, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueGramPerLiter(GramPerLiter, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueMicrometer(Micrometer, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueMilliOsmolesPerKilogram(
    MilliOsmolesPerKilogram, TNullableQuantityValue
):
    pass


@dataclass
class TNullableQuantityValueMillimeterOfMercury(
    MillimeterOfMercury, TNullableQuantityValue
):
    pass


@dataclass
class TNullableQuantityValueMillimolePerLiter(
    MillimolePerLiter, TNullableQuantityValue
):
    pass


@dataclass
class TNullableQuantityValueMillionCellsPerMilliliter(
    MillionCellsPerMilliliter, TNullableQuantityValue
):
    pass


@dataclass
class TNullableQuantityValueOpticalDensity(OpticalDensity, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValuePH(PH, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValuePercent(Percent, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueTODO(TODO, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueUnitPerLiter(UnitPerLiter, TNullableQuantityValue):
    pass


@dataclass
class TNullableQuantityValueUnitless(Unitless, TNullableQuantityValue):
    pass
