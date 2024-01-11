from dataclasses import dataclass
from typing import Optional


@dataclass
class HasUnit:
    unit: Optional[str]


@dataclass
class Centimeter(HasUnit):
    unit: Optional[str] = "cm"


@dataclass
class Millimeter(HasUnit):
    unit: Optional[str] = "mm"


@dataclass
class Nanometer(HasUnit):
    unit: Optional[str] = "nm"


@dataclass
class Micrometer(HasUnit):
    unit: Optional[str] = "μm"


@dataclass
class Hertz(HasUnit):
    unit: Optional[str] = "Hz"


@dataclass
class CubicMillimeter(HasUnit):
    unit: Optional[str] = "mm^3"


@dataclass
class Unitless(HasUnit):
    unit: Optional[str] = "(unitless)"


@dataclass
class SecondTime(HasUnit):
    unit: Optional[str] = "s"


@dataclass
class Percent(HasUnit):
    unit: Optional[str] = "%"


@dataclass
class Cell(HasUnit):
    unit: Optional[str] = "cell"


@dataclass
class Microliter(HasUnit):
    unit: Optional[str] = "μL"


@dataclass
class NumberPerMicroliter(HasUnit):
    unit: Optional[str] = "#/μL"


@dataclass
class MilliSecond(HasUnit):
    unit: Optional[str] = "ms"


@dataclass
class MillionCellsPerMilliliter(HasUnit):
    unit: Optional[str] = "10^6 cells/mL"


@dataclass
class TODO(HasUnit):
    unit: Optional[str] = "TODO"


@dataclass
class DegreeCelsius(HasUnit):
    unit: Optional[str] = "degC"


@dataclass
class Number(HasUnit):
    unit: Optional[str] = "#"


@dataclass
class NanogramPerMicroliter(HasUnit):
    unit: Optional[str] = "ng/uL"


@dataclass
class MicrogramPerMicroliter(HasUnit):
    unit: Optional[str] = "ug/uL"


@dataclass
class PicogramPerMilliliter(HasUnit):
    unit: Optional[str] = "pg/mL"


@dataclass
class NanogramPerMilliliter(HasUnit):
    unit: Optional[str] = "ng/mL"


@dataclass
class MicrogramPerMilliliter(HasUnit):
    unit: Optional[str] = "ug/mL"


@dataclass
class MilligramPerMilliliter(HasUnit):
    unit: Optional[str] = "mg/mL"


@dataclass
class GramPerLiter(HasUnit):
    unit: Optional[str] = "g/L"


@dataclass
class UnitPerLiter(HasUnit):
    unit: Optional[str] = "U/L"


@dataclass
class MillimeterOfMercury(HasUnit):
    unit: Optional[str] = "mmHg"


@dataclass
class OpticalDensity(HasUnit):
    unit: Optional[str] = "OD"


@dataclass
class PH(HasUnit):
    unit: Optional[str] = "pH"


@dataclass
class MilliOsmolesPerKilogram(HasUnit):
    unit: Optional[str] = "mosm/kg"


@dataclass
class MillimolePerLiter(HasUnit):
    unit: Optional[str] = "mmol/L"


@dataclass
class MilliAbsorbanceUnit(HasUnit):
    unit: Optional[str] = "mAU"


@dataclass
class RelativeFluorescenceUnit(HasUnit):
    unit: Optional[str] = "RFU"


@dataclass
class RelativeLightUnit(HasUnit):
    unit: Optional[str] = "RLU"


@dataclass
class SquareCentimetersPerGram(HasUnit):
    unit: Optional[str] = "cm^2/g"
