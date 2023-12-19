from dataclasses import dataclass
from typing import Optional


@dataclass
class Centimeter:
    unit: Optional[str] = "cm"


@dataclass
class Millimeter:
    unit: Optional[str] = "mm"


@dataclass
class Nanometer:
    unit: Optional[str] = "nm"


@dataclass
class Micrometer:
    unit: Optional[str] = "μm"


@dataclass
class Hertz:
    unit: Optional[str] = "Hz"


@dataclass
class CubicMillimeter:
    unit: Optional[str] = "mm^3"


@dataclass
class Unitless:
    unit: Optional[str] = "(unitless)"


@dataclass
class SecondTime:
    unit: Optional[str] = "s"


@dataclass
class Percent:
    unit: Optional[str] = "%"


@dataclass
class Cell:
    unit: Optional[str] = "cell"


@dataclass
class Microliter:
    unit: Optional[str] = "μL"


@dataclass
class NumberPerMicroliter:
    unit: Optional[str] = "#/μL"


@dataclass
class MilliSecond:
    unit: Optional[str] = "ms"


@dataclass
class MillionCellsPerMilliliter:
    unit: Optional[str] = "10^6 cells/mL"


@dataclass
class TODO:
    unit: Optional[str] = "TODO"


@dataclass
class DegreeCelsius:
    unit: Optional[str] = "degC"


@dataclass
class Number:
    unit: Optional[str] = "#"


@dataclass
class NanogramPerMicroliter:
    unit: Optional[str] = "ng/uL"


@dataclass
class MicrogramPerMicroliter:
    unit: Optional[str] = "ug/uL"


@dataclass
class PicogramPerMilliliter:
    unit: Optional[str] = "pg/mL"


@dataclass
class Milliliter:
    unit: Optional[str] = "mL"


@dataclass
class NanogramPerMilliliter:
    unit: Optional[str] = "ng/mL"


@dataclass
class MicrogramPerMilliliter:
    unit: Optional[str] = "ug/mL"


@dataclass
class MilligramPerMilliliter:
    unit: Optional[str] = "mg/mL"


@dataclass
class GramPerLiter:
    unit: Optional[str] = "g/L"


@dataclass
class UnitPerLiter:
    unit: Optional[str] = "U/L"


@dataclass
class MillimeterOfMercury:
    unit: Optional[str] = "mmHg"


@dataclass
class OpticalDensity:
    unit: Optional[str] = "OD"


@dataclass
class PH:
    unit: Optional[str] = "pH"


@dataclass
class MilliOsmolesPerKilogram:
    unit: Optional[str] = "mosm/kg"


@dataclass
class MillimolePerLiter:
    unit: Optional[str] = "mmol/L"


@dataclass
class MilliAbsorbanceUnit:
    unit: Optional[str] = "mAU"


@dataclass
class RelativeFluorescenceUnit:
    unit: Optional[str] = "RFU"


@dataclass
class RelativeLightUnit:
    unit: Optional[str] = "RLU"


@dataclass
class SquareCentimetersPerGram:
    unit: Optional[str] = "cm^2/g"
