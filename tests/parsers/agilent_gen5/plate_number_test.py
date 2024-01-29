import pytest

from allotropy.parsers.agilent_gen5.plate_data import PlateNumber


def test_plate_number_parse_datetime() -> None:
    date_ = "1/2/2024"
    time_ = "10:48:38 AM"
    datetime_ = PlateNumber._parse_datetime(date_, time_)
    assert datetime_ == "2024-01-02T10:48:38"


def test_plate_number_parse_datetime_fails() -> None:
    date_ = "1/2/2024"
    time_ = "10:48:38"
    msg = "time data '1/2/2024 10:48:38' does not match format '%m/%d/%Y %I:%M:%S %p'"
    # TODO: should raise AllotropeConversionError
    with pytest.raises(ValueError, match=msg):
        PlateNumber._parse_datetime(date_, time_)
