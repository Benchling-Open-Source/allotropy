from dataclasses import dataclass


@dataclass
class HasUnit:
    # TODO(brian): Ideally this wouldn't have a default value.
    unit: str = ""


@dataclass
class Centimeter(HasUnit):
    unit = "cm"


@dataclass
class Millimeter(HasUnit):
    unit = "mm"


@dataclass
class Nanometer(HasUnit):
    unit = "nm"


@dataclass
class Micrometer(HasUnit):
    unit = "μm"


@dataclass
class Hertz(HasUnit):
    unit = "Hz"


@dataclass
class CubicMillimeter(HasUnit):
    unit = "mm^3"


@dataclass
class Unitless(HasUnit):
    unit = "(unitless)"


@dataclass
class SecondTime(HasUnit):
    unit = "s"


@dataclass
class Percent(HasUnit):
    unit = "%"


@dataclass
class Cell(HasUnit):
    unit = "cell"


@dataclass
class Microliter(HasUnit):
    unit = "μL"


@dataclass
class NumberPerMicroliter(HasUnit):
    unit = "#/μL"


@dataclass
class MilliSecond(HasUnit):
    unit = "ms"


@dataclass
class MillionCellsPerMilliliter(HasUnit):
    unit = "10^6 cells/mL"


@dataclass
class TODO(HasUnit):
    unit = "TODO"


@dataclass
class DegreeCelsius(HasUnit):
    unit = "degC"


@dataclass
class Number(HasUnit):
    unit = "#"


@dataclass
class NanogramPerMicroliter(HasUnit):
    unit = "ng/uL"


@dataclass
class MicrogramPerMicroliter(HasUnit):
    unit = "ug/uL"


@dataclass
class PicogramPerMilliliter(HasUnit):
    unit = "pg/mL"


@dataclass
class NanogramPerMilliliter(HasUnit):
    unit = "ng/mL"


@dataclass
class MicrogramPerMilliliter(HasUnit):
    unit = "ug/mL"


@dataclass
class MilligramPerMilliliter(HasUnit):
    unit = "mg/mL"


@dataclass
class GramPerLiter(HasUnit):
    unit = "g/L"


@dataclass
class UnitPerLiter(HasUnit):
    unit = "U/L"


@dataclass
class MillimeterOfMercury(HasUnit):
    unit = "mmHg"


@dataclass
class OpticalDensity(HasUnit):
    unit = "OD"


@dataclass
class PH(HasUnit):
    unit = "pH"


@dataclass
class MilliOsmolesPerKilogram(HasUnit):
    unit = "mosm/kg"


@dataclass
class MillimolePerLiter(HasUnit):
    unit = "mmol/L"


@dataclass
class MilliAbsorbanceUnit(HasUnit):
    unit = "mAU"


@dataclass
class RelativeFluorescenceUnit(HasUnit):
    unit = "RFU"


@dataclass
class RelativeLightUnit(HasUnit):
    unit = "RLU"


@dataclass
class SquareCentimetersPerGram(HasUnit):
    unit = "cm^2/g"
