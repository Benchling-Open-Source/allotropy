import re
from unittest import mock

import pandas as pd
import pytest

from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Analyte,
    Calibration,
    Error,
    StatisticDimension,
    StatisticsDocument,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.luminex_xponent import constants
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    create_calibration,
    Header,
    Measurement,
    MeasurementList,
)
from allotropy.parsers.utils.pandas import SeriesData


def get_result_lines() -> list[str]:
    return [
        "Results,,,,,,,,,,,,,,,,,,,,,,,",
        ",,,,,,,,,,,,,,,,,,,,,,,",
        '"DataType:","Median"',
        "Location,Sample,alpha,bravo,Total Events",
        '"1(1,A1)",Unknown1,10921.5,37214,881',
        "",
        '"DataType:","Count"',
        "Location,Sample,alpha,bravo,Total Events",
        '"1(1,A1)",Unknown1,30,42,881',
        "",
        '"DataType:","Units"',
        "Analyte:,alpha,bravo",
        "BeadID:,28,35",
        "Units:,Bead,Bead",
        "",
        '"DataType:","Dilution Factor"',
        "Location,Sample,Dilution Factor",
        '"1(1,A1)",Unknown1,1',
        "",
        '"DataType:","Warnings/Errors",',
        "Location,Status,Message",
        '"1,A1",Warning,Warning msg. (0x4FF010AB)',
        '"1,A1",Warning,Another Warning.',
        "",
    ]


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
    header = Header.create(data, minimum_assay_bead_count_setting=10)

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
        minimum_assay_bead_count_setting=10,
    )


@pytest.mark.parametrize(
    "required_col",
    [
        "BatchStartTime",
        "ProtocolPlate",
    ],
)
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
    if required_col == "ProtocolPlate":
        error_msg = (
            "Unable to find required value 'ProtocolPlate' data in header block."
        )

    with pytest.raises(AllotropeConversionError, match=error_msg):
        Header.create(
            data.drop(columns=[required_col]), minimum_assay_bead_count_setting=100
        )


def test_create_calibration_item() -> None:
    name = "Device Calibration"
    report = "Passed"
    time = "05/17/2023 09:25:11"

    assert create_calibration(
        SeriesData(pd.Series([name, f"{report} {time}"]))
    ) == Calibration(name, report, time)


def test_create_calibration_item_invalid_line_format() -> None:
    bad_line = "Bad line."
    data = SeriesData(pd.Series([bad_line]))
    error = (
        f"Expected at least two columns on the calibration line, got:\n{data.series}"
    )
    with pytest.raises(AllotropeConversionError, match=error):
        create_calibration(data)


def test_create_calibration_item_invalid_calibration_result() -> None:
    bad_result = "bad_result"
    error = f"Invalid calibration result format, expected to split into two values, got: ['{bad_result}']"
    with pytest.raises(AllotropeConversionError, match=re.escape(error)):
        create_calibration(SeriesData(pd.Series(["Last CalReport", bad_result])))


def test_create_measurement_list() -> None:
    results_data = LuminexXponentReader._get_results(CsvReader(get_result_lines()))
    with mock.patch(
        "allotropy.parsers.luminex_xponent.luminex_xponent_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        measurement_list = MeasurementList.create(results_data)

    assert measurement_list == MeasurementList(
        measurements=[
            Measurement(
                identifier="dummy_id",
                sample_identifier="Unknown1",
                location_identifier="A1",
                dilution_factor_setting=1,
                assay_bead_count=881,
                analytes=[
                    Analyte(
                        identifier="dummy_id",
                        name="alpha",
                        assay_bead_identifier="28",
                        assay_bead_count=30,
                        statistics=[
                            StatisticsDocument(
                                statistical_feature="fluorescence",
                                statistic_dimensions=[
                                    StatisticDimension(
                                        value=10921.5,
                                        unit="RFU",
                                        statistic_datum_role=TStatisticDatumRole.median_role,
                                    )
                                ],
                            )
                        ],
                    ),
                    Analyte(
                        identifier="dummy_id",
                        name="bravo",
                        assay_bead_identifier="35",
                        assay_bead_count=42,
                        statistics=[
                            StatisticsDocument(
                                statistical_feature="fluorescence",
                                statistic_dimensions=[
                                    StatisticDimension(
                                        value=37214,
                                        unit="RFU",
                                        statistic_datum_role=TStatisticDatumRole.median_role,
                                    )
                                ],
                            )
                        ],
                    ),
                ],
                errors=[
                    Error(error="Warning msg. (0x4FF010AB)"),
                    Error(error="Another Warning."),
                ],
            )
        ]
    )


@pytest.mark.parametrize(
    "table_name",
    constants.REQUIRED_SECTIONS,
)
def test_create_measurement_list_without_required_table_then_raise(
    table_name: str,
) -> None:
    results_data = {
        section: pd.DataFrame()
        for section in constants.REQUIRED_SECTIONS
        if section != table_name
    }

    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            f"Unable to parse input file, missing expected sections: ['{table_name}']."
        ),
    ):
        MeasurementList.create(results_data)
