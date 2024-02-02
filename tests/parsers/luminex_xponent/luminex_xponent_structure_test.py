import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    Analyte,
    CalibrationItem,
    Data,
    Header,
    Measurement,
    MeasurementList,
)
from tests.parsers.luminex_xponent.luminex_xponent_data import get_data, get_reader


def get_result_lines(remove: str = "") -> list[str]:
    lines = [
        "DataType:,Median,",
        "Location,Sample,alpha,bravo,Total Events",
        '"1(1,A1)",Unknown1,10921.5,37214,881',
        ",,",
        "DataType:,Count,",
        "Location,Sample,alpha,bravo,Total Events",
        '"1(1,A1)",Unknown1,30,42,881',
        ",,",
        "DataType:,Units,",
        "Analyte:,alpha,bravo",
        "BeadID:,28,35",
        "Units:,Bead,Bead",
        ",,",
        "DataType:,Dilution Factor,",
        "Location,Sample,Dilution Factor",
        '"1(1,A1)",Unknown1,1',
        ",,",
        "DataType:,Warnings/Errors,",
        "Location,Status,Message",
        '"1,A1",Warning,Warning msg. (0x4FF010AB)',
        '"1,A1",Warning,Another Warning.',
        ",,",
    ]
    headers = {
        "Median": 0,
        "Count": 4,
        "Units": 8,
        "Dilution Factor": 13,
        "Warnings/Errors": 17,
    }

    if remove in headers:
        del lines[headers[remove]]

    return lines


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
        sample_volume_setting=1,  # SampleVolume
        plate_well_count=10,  # ProtocolPlate, column 5 (after Type)
        measurement_time="1/17/2024 7:41:29 AM",  # BatchStartTime
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

    error_msg = f"Expected non-null value for {required_col}."
    if required_col in ("Program", "ProtocolPlate"):
        error_msg = f"Unable to find {required_col} data on header block."

    with pytest.raises(AllotropeConversionError, match=error_msg):
        Header.create(data.drop(columns=[required_col]))


@pytest.mark.short
def test_create_calibration_item() -> None:
    name = "Device Calibration"
    report = "Passed"

    calibration_item = CalibrationItem.create(
        f"Last {name},{report} 05/17/2023 09:25:11"
    )

    assert calibration_item == CalibrationItem(name, report, "05/17/2023 09:25:11")


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
def test_create_measurement_list() -> None:
    reader = CsvReader(get_result_lines())

    assert MeasurementList.create(reader) == MeasurementList(
        measurements=[
            Measurement(
                sample_identifier="Unknown1",
                location_identifier="A1",
                dilution_factor_setting=1,
                assay_bead_count=881,
                analytes=[
                    Analyte(
                        analyte_name="alpha",
                        assay_bead_identifier="28",
                        assay_bead_count=30,
                        fluorescence=10921.5,
                    ),
                    Analyte(
                        analyte_name="bravo",
                        assay_bead_identifier="35",
                        assay_bead_count=42,
                        fluorescence=37214,
                    ),
                ],
                errors=[
                    "Warning msg. (0x4FF010AB)",
                    "Another Warning.",
                ],
            )
        ]
    )


@pytest.mark.parametrize(
    "table_name",
    ["Median", "Count", "Units", "Dilution Factor"],
)
@pytest.mark.short
def test_create_measurement_list_without_required_table_then_raise(
    table_name: str,
) -> None:
    reader = CsvReader(get_result_lines(remove=table_name))

    with pytest.raises(
        AllotropeConversionError, match=f"Unable to find {table_name} table."
    ):
        MeasurementList.create(reader)


def test_create_data() -> None:
    data = Data.create(get_reader())

    assert data == get_data()
