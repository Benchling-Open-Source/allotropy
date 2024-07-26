import pytest

from allotropy.parsers.utils.iterables import get_first_not_none


@pytest.mark.short
def test_get_first_not_none() -> None:
    assert get_first_not_none(lambda x: x if x > 2 else None, [1, 2, 3]) == 3
    assert get_first_not_none(lambda x: x if x > 3 else None, [1, 2, 3]) is None
    # Check falsey zero
    assert get_first_not_none(lambda x: x if x == 0 else None, [1, 0]) == 0
