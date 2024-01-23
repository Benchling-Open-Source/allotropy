import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    CalibrationItem,
    Data,
    Header,
)
from tests.parsers.luminex_xponent.luminex_xponent_data import get_data, get_reader


@pytest.mark.short
def test_create_header() -> None:
    data = pd.DataFrame.from_dict(
        {
            "Program": ["xPonent", None, "Model"],
            "Build": ["1.1.0"],
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
        software_version="1.1.0",  # Build
        equipment_serial_number="SN1234",  # SN
        analytical_method_identifier="Order66",  # ProtocolName
        method_version="5",  # ProtocolVersion
        experimental_data_identifier="ABC_0000",  # Batch
        sample_volume_setting="1 uL",  # SampleVolume
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
        "Build",
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
            "Build": ["1.0.1"],
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


@pytest.mark.short
def test_create_calibration_item() -> None:
    name = "Device Calibration"
    report = "Passed"

    calibration_item = CalibrationItem.create(
        f"Last {name},{report} 05/17/2023 09:25:11"
    )

    assert calibration_item == CalibrationItem(name, report, "2023-05-17T09:25:11")


@pytest.mark.short
def test_create_calibration_item_invalid_line_format() -> None:
    bad_line = "Bad line."
    error = f"Expected at least two columns on the calibration line, got: {bad_line}"
    with pytest.raises(AllotropeConversionError, match=error):
        CalibrationItem.create(bad_line)


@pytest.mark.short
def test_create_calibration_item_invalid_calibration_result() -> None:
    bad_result = "bad_result"
    bad_line = f"Last CalReport,{bad_result}"
    error = f"Invalid calibration result format, got: {bad_result}"
    with pytest.raises(AllotropeConversionError, match=error):
        CalibrationItem.create(bad_line)


@pytest.mark.short
def test_create_calibration_item_invalid_calibration_time() -> None:
    invalid_time = "bad datetime"
    bad_line = f"Last CalReport, Passed {invalid_time}"
    error = "Invalid calibration time format."
    with pytest.raises(AllotropeConversionError, match=error):
        CalibrationItem.create(bad_line)


def test_create_data() -> None:
    data = Data.create(get_reader())

    assert data == get_data()
