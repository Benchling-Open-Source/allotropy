from dataclasses import fields, MISSING

# We must import this to get all subclasses of TQuantityValue in scope
import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue


def _clean_unit(unit: str) -> str:
    return unit.replace("µ", "u").replace("μ", "u")


def _make_unit_entry(quantity_value: type[TQuantityValue]) -> str | None:
    unit_field = next(field for field in fields(quantity_value) if field.name == "unit")
    if unit_field.default == MISSING:
        return None
    return _clean_unit(str(unit_field.default))


UNIT_TO_PROPERTY = {
    unit_entry: quantity_value
    for unit_entry, quantity_value in [
        (_make_unit_entry(quantity_value), quantity_value)
        for quantity_value in TQuantityValue.__subclasses__()
    ]
    if unit_entry
}

# Some input files have units with incorrect capitalization. Try to handle this by checking with case insensitive.
# We don't do this by default, however, because there are some cases where capitalization matters, e.g.
# namometer (nm) != nanomolar (nM).
LOWER_UNIT_TO_PROPERTY = {
    unit.lower(): quantity_value for unit, quantity_value in UNIT_TO_PROPERTY.items()
}


def get_quantity_class(
    unit: str | None, default: type[TQuantityValue] | None = None
) -> type[TQuantityValue] | None:
    clean_unit = _clean_unit(unit or "")
    # Try to get case-sensitive unit, falling back to default if provided, finally checking case-insensitive unit,
    # which may not always have the correct result.
    return (
        UNIT_TO_PROPERTY.get(clean_unit)
        or default
        or LOWER_UNIT_TO_PROPERTY.get(clean_unit.lower())
    )
