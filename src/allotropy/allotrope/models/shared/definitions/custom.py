from dataclasses import dataclass

from allotropy.allotrope.models.shared.definitions.definitions import (
    TNullableQuantityValue,
    TQuantityValue,
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
class TQuantityValueCentimeter(Centimeter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMillimeter(Millimeter, TQuantityValue):
    pass


@dataclass
class TQuantityValueNanometer(Nanometer, TQuantityValue):
    pass


@dataclass
class TQuantityValueMicrometer(Micrometer, TQuantityValue):
    pass


@dataclass
class TQuantityValueHertz(Hertz, TQuantityValue):
    pass


@dataclass
class TQuantityValueCubicMillimeter(CubicMillimeter, TQuantityValue):
    pass


@dataclass
class TQuantityValueUnitless(Unitless, TQuantityValue):
    pass


@dataclass
class TQuantityValueSecondTime(SecondTime, TQuantityValue):
    pass


@dataclass
class TQuantityValuePercent(Percent, TQuantityValue):
    pass


@dataclass
class TQuantityValueCell(Cell, TQuantityValue):
    pass


@dataclass
class TQuantityValueMicroliter(Microliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueNumberPerMicroliter(NumberPerMicroliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMilliSecond(MilliSecond, TQuantityValue):
    pass


@dataclass
class TQuantityValueMillionCellsPerMilliliter(
    MillionCellsPerMilliliter, TQuantityValue
):
    pass


@dataclass
class TQuantityValueTODO(TODO, TQuantityValue):
    pass


@dataclass
class TQuantityValueGramPerLiter(GramPerLiter, TQuantityValue):
    pass


@dataclass
class TQuantityValueDegreeCelsius(DegreeCelsius, TQuantityValue):
    pass


@dataclass
class TQuantityValueNumber(Number, TQuantityValue):
    pass


@dataclass
class TQuantityValueNanogramPerMicroliter(NanogramPerMicroliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMicrogramPerMicroliter(MicrogramPerMicroliter, TQuantityValue):
    pass


@dataclass
class TQuantityValuePicogramPerMilliliter(PicogramPerMilliliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueNanogramPerMilliliter(NanogramPerMilliliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMicrogramPerMilliliter(MicrogramPerMilliliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMilligramPerMilliliter(MilligramPerMilliliter, TQuantityValue):
    pass


@dataclass
class TQuantityValueUnitPerLiter(UnitPerLiter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMillimeterOfMercury(MillimeterOfMercury, TQuantityValue):
    pass


@dataclass
class TQuantityValueOpticalDensity(OpticalDensity, TQuantityValue):
    pass


@dataclass
class TQuantityValuePH(PH, TQuantityValue):
    pass


@dataclass
class TQuantityValueMilliOsmolesPerKilogram(MilliOsmolesPerKilogram, TQuantityValue):
    pass


@dataclass
class TQuantityValueMillimolePerLiter(MillimolePerLiter, TQuantityValue):
    pass


@dataclass
class TQuantityValueMilliAbsorbanceUnit(MilliAbsorbanceUnit, TQuantityValue):
    pass


@dataclass
class TQuantityValueRelativeFluorescenceUnit(RelativeFluorescenceUnit, TQuantityValue):
    pass


@dataclass
class TQuantityValueRelativeLightUnit(RelativeLightUnit, TQuantityValue):
    pass


@dataclass
class TQuantityValueSquareCentimetersPerGram(SquareCentimetersPerGram, TQuantityValue):
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
