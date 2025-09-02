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
    MultipleDatasetParser,
    SingleDatasetParser,
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
    header_row = SeriesData(data.iloc[0])
    header = Header.create(data, header_row, minimum_assay_bead_count_setting=10)

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
        custom_info={
            "Country Code": None,
            "ProtocolDevelopingCompany": None,
            "Version": None,
            "BatchStopTime": None,
            "ProtocolDescription": None,
        },
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
        data_without_col = data.drop(columns=[required_col])
        header_row = SeriesData(data_without_col.iloc[0])
        Header.create(
            data_without_col, header_row, minimum_assay_bead_count_setting=100
        )


def test_create_calibration_item() -> None:
    name = "Device Calibration"
    report = "Passed"
    time = "05/17/2023 09:25:11"

    assert create_calibration(
        SeriesData(pd.Series([name, f"{report} {time}"]))
    ) == Calibration(name, time, report)


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
    error = f"Invalid calibration result format, got: ['{bad_result}']"
    with pytest.raises(AllotropeConversionError, match=re.escape(error)):
        create_calibration(SeriesData(pd.Series(["Last CalReport", bad_result])))


def test_create_measurement_list() -> None:
    results_data = MultipleDatasetParser._get_results(CsvReader(get_result_lines()))

    # Create a mock header_data DataFrame for testing
    mock_header_data = pd.DataFrame.from_dict(
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
            "BatchDescription": ["Test Batch Description"],
        },
        orient="index",
    ).T

    with mock.patch(
        "allotropy.parsers.luminex_xponent.luminex_xponent_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        header_row = SeriesData(mock_header_data.iloc[0])
        measurement_list = MeasurementList.create(results_data, header_row)

    assert measurement_list == MeasurementList(
        measurements=[
            Measurement(
                identifier="dummy_id",
                sample_identifier="Unknown1",
                location_identifier="A1",
                dilution_factor_setting=1.0,
                assay_bead_count=881.0,
                analytes=[
                    Analyte(
                        identifier="dummy_id",
                        name="alpha",
                        assay_bead_identifier="28",
                        assay_bead_count=30.0,
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
                        assay_bead_count=42.0,
                        statistics=[
                            StatisticsDocument(
                                statistical_feature="fluorescence",
                                statistic_dimensions=[
                                    StatisticDimension(
                                        value=37214.0,
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
                calculated_data=[],
                measurement_custom_info={
                    "ProtocolName": "Order66",
                    "ProtocolVersion": 5.0,
                    "ProtocolReporterGain": "Pro MAP",
                    "SampleVolume": "1 uL",
                    "Build": "1.1.0",
                    "Program": "xPonent",
                    "SN": "SN1234",
                    "ComputerName": "AAA000",
                    "Batch": "ABC_0000",
                    "BatchStartTime": "1/17/2024 7:41:29 AM",
                },
                sample_custom_info={
                    "BatchDescription": "Test Batch Description",
                    "PanelName": None,
                    "BeadType": None,
                },
                device_control_custom_info={
                    "ProtocolHeater": None,
                    "DDGate": None,
                    "SampleTimeout": None,
                    "ProtocolAnalysis": None,
                    "ProtocolMicrosphere": None,
                    "PlateReadDirection": None,
                },
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

    # Create a mock header_data DataFrame for testing
    mock_header_data = pd.DataFrame.from_dict(
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
            "BatchDescription": ["Test Batch Description"],
        },
        orient="index",
    ).T

    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            f"Unable to parse input file, missing expected sections: ['{table_name}']."
        ),
    ):
        header_row = SeriesData(mock_header_data.iloc[0])
        MeasurementList.create(results_data, header_row)


class TestSingleDatasetParser:
    header_prefix = "INSTRUMENT TYPE,SERIAL NUMBER,SOFTWARE VERSION,PLATE NAME,PLATE START,WELL LOCATION,SAMPLE ID"
    row_prefix = "LX200,SN-1,3.1.0,Plate-1,2024-01-01 10:00:00,A1,S1"

    def test_parse_header_splits_analyte_and_metric(self) -> None:
        analyte, metric = SingleDatasetParser.parse_header("REPORTER 1 AVERAGE MFI")  # type: ignore[misc]
        assert analyte == "REPORTER 1"
        assert metric == "AVERAGE MFI"

        analyte2, metric2 = SingleDatasetParser.parse_header("R42 TRIMMED STANDARD DEVIATION")  # type: ignore[misc]
        assert analyte2 == "R42"
        assert metric2 == "TRIMMED STANDARD DEVIATION"

    def test_parse_header_returns_none_for_unknown_metric(self) -> None:
        assert SingleDatasetParser.parse_header("Alpha UnknownMetric") is None

    def test_parse_builds_results_and_units_and_dilution(self) -> None:
        # Minimal single-dataset CSV lines
        lines = [
            f"{self.header_prefix},alpha Median,alpha Count,bravo Median,bravo Count",
            f"{self.row_prefix},100.5,30,200.0,50",
        ]

        results, header, calibration, min_beads = SingleDatasetParser.parse(lines)

        # Expected sections
        assert "Median" in results
        assert "Count" in results
        assert "Units" in results
        assert "Dilution Factor" in results

        # Verify Count section totals and columns
        count_df = results["Count"]
        assert "Total Events" in count_df.columns
        # Index should be location-based
        assert "1(1,A1)" in count_df.index
        # Sample column present
        assert count_df.loc["1(1,A1)", "Sample"] == "S1"
        # Analyte columns exist
        assert "alpha" in count_df.columns and "bravo" in count_df.columns

        # Verify Median section values present for analytes
        median_df = results["Median"]
        assert float(median_df.loc["1(1,A1)", "alpha"]) == 100.5  # type: ignore[arg-type]
        assert float(median_df.loc["1(1,A1)", "bravo"]) == 200.0  # type: ignore[arg-type]

        # Basic checks on Units and Dilution Factor tables
        units_df = results["Units"]
        assert "alpha" in units_df.columns and "bravo" in units_df.columns
        assert "Units:" in units_df.index

        dilution_df = results["Dilution Factor"]
        assert "Dilution Factor" in dilution_df.columns

    def test_parse_preserves_units_and_dilution_factor_from_input(self) -> None:
        # Input explicitly contains per-analyte Units and Dilution Factor metrics
        lines = [
            f"{self.header_prefix},alpha COUNT,bravo COUNT, alpha UNITS,bravo UNITS,alpha DILUTION FACTOR,bravo DILUTION FACTOR",
            f"{self.row_prefix},1.0,2.0,3.0,4.0,5.0,6.0",
        ]

        results, header, calibration, min_beads = SingleDatasetParser.parse(lines)

        # Sections detected from input
        assert "Units" in results
        assert "Dilution Factor" in results

        # Values preserved from input in the corresponding sections
        units_df = results["Units"]
        assert float(units_df.loc["BeadID:", "alpha"]) == 3.0  # type: ignore[arg-type]
        assert float(units_df.loc["BeadID:", "bravo"]) == 4.0  # type: ignore[arg-type]

        dilution_df = results["Dilution Factor"]
        assert float(dilution_df.loc["1(1,A1)", "alpha"]) == 5.0  # type: ignore[arg-type]
        assert float(dilution_df.loc["1(1,A1)", "bravo"]) == 6.0  # type: ignore[arg-type]

    def test_header_contains_serial_and_plate_start(self) -> None:
        # Minimal input with only the fixed columns
        lines = [
            f"{self.header_prefix}",
            f"{self.row_prefix}",
        ]

        _results, header, _calibration, _min_beads = SingleDatasetParser.parse(lines)

        # Values should be propagated into the header table
        assert header["SN"].iloc[0] == "SN-1"
        assert header["BatchStartTime"].iloc[0] == "2024-01-01 10:00:00"

    def test_is_single_dataset_true_with_expected_header_line(self) -> None:
        lines = [
            "INSTRUMENT TYPE,SERIAL NUMBER,SOFTWARE VERSION,PLATE NAME,PLATE START,WELL LOCATION,SAMPLE ID,Analyte 1 Median",
            "LX200,1234,3.1.0,PlateA,2024-01-01,A1,Sample-1,100",
        ]
        assert LuminexXponentReader._is_single_dataset(lines) is True

    def test_is_single_dataset_false_missing_one_keyword(self) -> None:
        # Missing "SAMPLE ID"
        lines = [
            "INSTRUMENT TYPE,SERIAL NUMBER,SOFTWARE VERSION,PLATE NAME,PLATE START,WELL LOCATION,Analyte 1 Median",
            "LX200,1234,3.1.0,PlateA,2024-01-01,A1,100",
        ]
        assert LuminexXponentReader._is_single_dataset(lines) is False

    def test_is_single_dataset_false_empty_input(self) -> None:
        assert LuminexXponentReader._is_single_dataset(["RANDOM TEXT"]) is False

    def test_is_single_dataset_true_ignores_rest_of_line_content(self) -> None:
        # Extra columns should be ignored as detection is substring-based
        lines = [
            "random prefix,INSTRUMENT TYPE,foo,WELL LOCATION,bar,SAMPLE ID,baz",
            "",
        ]
        assert LuminexXponentReader._is_single_dataset(lines) is True
