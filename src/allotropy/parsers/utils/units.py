from dataclasses import fields, MISSING

# We must import this to get all subclasses of TQuantityValue in scope
import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue


def _clean_unit(unit: str) -> str:
    return unit.lower().replace("µ", "u")


def _make_unit_entry(quantity_value: type[TQuantityValue]) -> str | None:
    unit_field = next(field for field in fields(quantity_value) if field.name == "unit")
    if unit_field.default == MISSING:
        return None
    return _clean_unit(str(unit_field.default))


UNIT_TO_PROPERTY = {
    _make_unit_entry(quantity_value): quantity_value
    for quantity_value in TQuantityValue.__subclasses__()
}


def get_quantity_class(
    unit: str | None, default: type[TQuantityValue] | None = None
) -> type[TQuantityValue] | None:
    return UNIT_TO_PROPERTY.get(_clean_unit(unit or ""), default)
