from dataclasses import fields

# We must import this to get all subclasses of TQuantityValue in scope
import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue

UNIT_TO_PROPERTY = {
    next(
        field for field in fields(quantity_value) if field.name == "unit"
    ).default: quantity_value
    for quantity_value in TQuantityValue.__subclasses__()
}


def get_quantity_class(
    unit: str | None, default: type[TQuantityValue] | None = None
) -> type[TQuantityValue] | None:
    return UNIT_TO_PROPERTY.get(unit, default)
