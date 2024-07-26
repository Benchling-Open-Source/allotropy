# We must import this to get all subclasses of TQuantityValue in scope
import pytest

import allotropy.allotrope.models.shared.definitions.custom  # noqa: F401
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.models.shared.definitions.units import (
    MillimolePerLiter,
    MillivoltTimesSecond,
    NanogramPerMicroliter,
)
from allotropy.parsers.utils.units import get_quantity_class
from allotropy.parsers.utils.values import assert_not_none


@pytest.mark.short
def test_get_quantity_class() -> None:
    for property_class in TQuantityValue.__subclasses__():
        # Typing does not know that all subclasses of TQuantityValue have default value for unit set.
        instance = property_class(value=1.0)  # type: ignore[call-arg]
        assert get_quantity_class(instance.unit) == property_class


@pytest.mark.short
def test_case_insensitive() -> None:
    assert assert_not_none(get_quantity_class("mmol/L")).unit == MillimolePerLiter.unit
    assert assert_not_none(get_quantity_class("MV.S")).unit == MillivoltTimesSecond.unit


@pytest.mark.short
def test_u_instead_of_micro() -> None:
    assert (
        assert_not_none(get_quantity_class("ng/ul")).unit == NanogramPerMicroliter.unit
    )
