from dataclasses import fields

import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue

UNIT_TO_PROPERTY = {
    next(
        field for field in fields(quantity_value) if field.name == "unit"
    ).default: quantity_value
    for quantity_value in TQuantityValue.__subclasses__()
}


def get_property_for_unit(unit: str) -> TQuantityValue | None:
    print(allotropy.allotrope.models.shared.definitions.custom.TQuantityValueNanogramPerMicroliter(value=0).unit)
    print(f"UNIT: {unit}")
    print(UNIT_TO_PROPERTY.get(unit))
    return UNIT_TO_PROPERTY.get(unit)
