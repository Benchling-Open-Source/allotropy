import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import Data, Header
from tests.parsers.luminex_xponent.luminex_xponent_data import get_data, get_reader


def test_create_header() -> None:
    data = pd.DataFrame.from_dict(
        {
            "Program": ["xPonent", None, "Model"],
            "SN": ["SN1234"],
            "Batch": ["ABC_0000"],
            "ComputerName": ["AAA000"],
            "ProtocolName": ["Order66"],
            "ProtocolVersion": ["5"],
            "SampleVolume": ["1 uL"],
            "BatchStartTime": ["1/17/2024 7:41:29 AM"],
            "ProtocolPlate": [None, None, "Type", 10],
            "ProtocolReporterGain": ["Pro MAP"],
        },
        orient="index",
    ).T
    header = Header.create(data)

    assert header == Header(
        model_number="Model",  # Program, col 4
        equipment_serial_number="SN1234",  # SN
        analytical_method_identifier="Order66",  # ProtocolName
        method_version="5",  # ProtocolVersion
        experimental_data_identifier="ABC_0000",  # Batch
        sample_volume="1 uL",  # SampleVolume
        plate_well_count=10,  # ProtocolPlate, column 5 (after Type)
        measurement_time="2024-01-17T07:41:29",  # BatchStartTime  MM/DD/YYY HH:MM:SS %p ->  YYYY-MM-DD HH:MM:SS
        detector_gain_setting="Pro MAP",  # ProtocolReporterGain
        analyst=None,  # Operator row
        data_system_instance_identifier="AAA000",  # ComputerName
    )


@pytest.mark.parametrize(
    "required_col",
    [
        "Program",
        "SN",
        "Batch",
        "ComputerName",
        "ProtocolName",
        "ProtocolVersion",
        "SampleVolume",
        "BatchStartTime",
        "ProtocolPlate",
        "ProtocolReporterGain",
    ],
)
@pytest.mark.short
def test_create_heder_without_required_col(required_col: str) -> None:
    data = pd.DataFrame.from_dict(
        {
            "Program": ["xPonent", None, "Model"],
            "SN": ["SN1234"],
            "Batch": ["ABC_0000"],
            "ComputerName": ["AAA000"],
            "ProtocolName": ["Order66"],
            "ProtocolVersion": ["5"],
            "SampleVolume": ["1 uL"],
            "BatchStartTime": ["1/17/2024 7:41:29 AM"],
            "ProtocolPlate": [None, None, "Type", 10],
            "ProtocolReporterGain": ["Pro MAP"],
        },
        orient="index",
    ).T
    with pytest.raises(AllotropeConversionError):
        Header.create(header_data=data.drop(columns=[required_col]))


def test_create_data() -> None:
    data = Data.create(get_reader())

    assert data == get_data()
