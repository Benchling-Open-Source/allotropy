import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.parsers.utils.units import get_property_for_unit


def test_get_property_for_unit() -> None:
    for property_class in TQuantityValue.__subclasses__():
        instance = property_class(value=1.0)
        assert get_property_for_unit(instance.unit) == property_class
