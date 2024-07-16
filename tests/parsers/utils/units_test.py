# We must import this to get all subclasses of TQuantityValue in scope
import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.parsers.utils.units import get_quantity_class


def test_get_quantity_class() -> None:
    for property_class in TQuantityValue.__subclasses__():
        # Typing does not know that all subclasses of TQuantityValue have default value for unit set.
        instance = property_class(value=1.0)  # type: ignore[call-arg]
        assert get_quantity_class(instance.unit) == property_class
