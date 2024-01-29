import pytest

from allotropy.parsers.agilent_gen5.plate_data import PlateNumber


@pytest.mark.parametrize(
    "date_,time_,expected",
    [
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38"),
        ("1/31/2024", "10:48:38 AM", "2024-01-31T10:48:38"),
        ("2/1/2024", "10:48:38 AM", "2024-02-01T10:48:38"),
    ],
)
def test_plate_number_parse_datetime(date_: str, time_: str, expected: str) -> None:
    datetime_ = PlateNumber._parse_datetime(date_, time_)
    assert datetime_ == expected


@pytest.mark.parametrize(
    "date_,time_,expected",
    [
        (
            "1/31/2024",
            "10:48:38",
            "time data '1/31/2024 10:48:38' does not match format '%m/%d/%Y %I:%M:%S %p'",
        ),
        (
            "31/1/2024",
            "10:48:38",
            "time data '31/1/2024 10:48:38' does not match format '%m/%d/%Y %I:%M:%S %p'",
        ),
        (
            "2/1/2024",
            "10:48:38",
            "time data '2/1/2024 10:48:38' does not match format '%m/%d/%Y %I:%M:%S %p'",
        ),
    ],
)
def test_plate_number_parse_datetime_fails(
    date_: str, time_: str, expected: str
) -> None:
    # TODO(brian): should raise AllotropeConversionError
    with pytest.raises(ValueError, match=expected):
        PlateNumber._parse_datetime(date_, time_)
