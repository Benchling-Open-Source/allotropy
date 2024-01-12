from abc import ABC, abstractmethod
from typing import final

UNITLESS = "(unitless)"


class HasUnit(ABC):
    @property
    @abstractmethod
    def unit(self) -> str:
        raise NotImplementedError


class HasUnitMethod(ABC):
    @classmethod
    def get_clazz_unit(cls) -> str:
        return cls._get_unit()

    @property
    @final
    def unit(self) -> str:
        return self._get_unit()

    @classmethod
    @abstractmethod
    def _get_unit(cls) -> str:
        raise NotImplementedError


class Centimeter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "cm"


class Millimeter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mm"


class Nanometer(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mm"


class Micrometer(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "μm"


class Hertz(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "Hz"


class CubicMillimeter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mm^3"


class Unitless(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return UNITLESS


class SecondTime(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "s"


class Percent(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "%"


class Cell(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "cell"


class Microliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "μL"


class NumberPerMicroliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "μL"


class MilliSecond(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "ms"


class MillionCellsPerMilliliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "10^6 cells/mL"


class TODO(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "TODO"


class DegreeCelsius(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "degC"


class Number(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "#"


class NanogramPerMicroliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "ng/uL"


class MicrogramPerMicroliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "ug/uL"


class PicogramPerMilliliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "pg/mL"


class NanogramPerMilliliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "pg/mL"


class MicrogramPerMilliliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "ug/mL"


class MilligramPerMilliliter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mg/mL"


class GramPerLiter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "g/L"


class UnitPerLiter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "U/L"


class MillimeterOfMercury(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mmHg"


class OpticalDensity(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "OD"


class PH(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "pH"


class MilliOsmolesPerKilogram(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mosm/kg"


class MillimolePerLiter(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mmol/L"


class MilliAbsorbanceUnit(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "mAU"


class RelativeFluorescenceUnit(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "RFU"


class RelativeLightUnit(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "RLU"


class SquareCentimetersPerGram(HasUnitMethod):
    @classmethod
    def _get_unit(cls) -> str:
        return "cm^2/g"
