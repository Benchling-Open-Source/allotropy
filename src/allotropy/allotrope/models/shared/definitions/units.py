from dataclasses import dataclass

UNITLESS = "(unitless)"


@dataclass
class HasUnit:
    unit: str


@dataclass
class Centimeter(HasUnit):
    unit: str = "cm"


@dataclass
class Millimeter(HasUnit):
    unit: str = "mm"


@dataclass
class Nanometer(HasUnit):
    unit: str = "nm"


@dataclass
class Micrometer(HasUnit):
    unit: str = "μm"


@dataclass
class Hertz(HasUnit):
    unit: str = "Hz"


@dataclass
class CubicMillimeter(HasUnit):
    unit: str = "mm^3"


@dataclass
class Unitless(HasUnit):
    unit: str = UNITLESS


@dataclass
class SecondTime(HasUnit):
    unit: str = "s"


@dataclass
class Percent(HasUnit):
    unit: str = "%"


@dataclass
class Cell(HasUnit):
    unit: str = "cell"


@dataclass
class Microliter(HasUnit):
    unit: str = "μL"


@dataclass
class NumberPerMicroliter(HasUnit):
    unit: str = "#/μL"


@dataclass
class MilliSecond(HasUnit):
    unit: str = "ms"


@dataclass
class MillionCellsPerMilliliter(HasUnit):
    unit: str = "10^6 cells/mL"


@dataclass
class TODO(HasUnit):
    unit: str = "TODO"


@dataclass
class DegreeCelsius(HasUnit):
    unit: str = "degC"


@dataclass
class Number(HasUnit):
    unit: str = "#"


@dataclass
class NanogramPerMicroliter(HasUnit):
    unit: str = "ng/uL"


@dataclass
class MicrogramPerMicroliter(HasUnit):
    unit: str = "ug/uL"


@dataclass
class PicogramPerMilliliter(HasUnit):
    unit: str = "pg/mL"


@dataclass
class NanogramPerMilliliter(HasUnit):
    unit: str = "ng/mL"


@dataclass
class MicrogramPerMilliliter(HasUnit):
    unit: str = "ug/mL"


@dataclass
class MilligramPerMilliliter(HasUnit):
    unit: str = "mg/mL"


@dataclass
class GramPerLiter(HasUnit):
    unit: str = "g/L"


@dataclass
class UnitPerLiter(HasUnit):
    unit: str = "U/L"


@dataclass
class MillimeterOfMercury(HasUnit):
    unit: str = "mmHg"


@dataclass
class OpticalDensity(HasUnit):
    unit: str = "OD"


@dataclass
class PH(HasUnit):
    unit: str = "pH"


@dataclass
class MilliOsmolesPerKilogram(HasUnit):
    unit: str = "mosm/kg"


@dataclass
class MillimolePerLiter(HasUnit):
    unit: str = "mmol/L"


@dataclass
class MilliAbsorbanceUnit(HasUnit):
    unit: str = "mAU"


@dataclass
class RelativeFluorescenceUnit(HasUnit):
    unit: str = "RFU"


@dataclass
class RelativeLightUnit(HasUnit):
    unit: str = "RLU"


@dataclass
class SquareCentimetersPerGram(HasUnit):
    unit: str = "cm^2/g"
