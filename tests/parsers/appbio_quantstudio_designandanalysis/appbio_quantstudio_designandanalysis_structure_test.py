from __future__ import annotations

import pandas as pd
import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Header,
    Result,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.standard_curve.structure import (
    StandardCurveWellList,
)
from allotropy.parsers.utils.pandas import SeriesData


def test_header_builder_returns_header_instance() -> None:
    header_contents = get_raw_header_contents()
    assert isinstance(Header.create(header_contents), Header)


def test_header_builder() -> None:
    measurement_time = "2010-10-01 01:44:54 AM EDT"
    device_identifier = "device1"
    model_number = "123"
    device_serial_number = "1234"
    measurement_method_identifier = "measurement ID"
    pcr_detection_chemistry = "detection1"
    passive_reference_dye_setting = "blue"
    experimental_data_identifier = "path/to/data_identifier.eds"

    header_contents = get_raw_header_contents(
        measurement_time=measurement_time,
        plate_well_count="96 Well 0.2-mL Block",
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        pcr_detection_chemistry=pcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        experimental_data_identifier=experimental_data_identifier,
        pcr_stage_number="Stage 2 Step 2",
        software_name_and_version="Design & Analysis Software v2.7.0",
        block_serial_number="1",
        heated_cover_serial_number="2",
    )

    assert Header.create(header_contents) == Header(
        measurement_time=measurement_time,
        plate_well_count=96,
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        pcr_detection_chemistry=pcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        barcode=None,
        analyst=None,
        experimental_data_identifier="data_identifier.eds",
        pcr_stage_number=2,
        software_name="Design & Analysis Software",
        software_version="2.7.0",
        block_serial_number="1",
        heated_cover_serial_number="2",
        well_volume=200,
        extra_data={},
    )


@pytest.mark.parametrize(
    "parameter,expected_error",
    [
        (
            "measurement_method_identifier",
            "Expected non-null value for Quantification Cycle Method.",
        ),
        ("plate_well_count", "Expected non-null value for Block Type."),
    ],
)
def test_header_builder_required_parameter_none_then_raise(
    parameter: str, expected_error: str
) -> None:
    header_contents = get_raw_header_contents(**{parameter: None})

    with pytest.raises(AllotropeConversionError, match=expected_error):
        Header.create(header_contents)


def test_header_builder_invalid_plate_well_count() -> None:
    header_contents = get_raw_header_contents(plate_well_count="0 plates")

    with pytest.raises(AllotropeConversionError):
        Header.create(header_contents)


def test_header_builder_no_header_then_raise() -> None:
    with pytest.raises(AllotropeConversionError):
        Header.create(SeriesData(pd.Series()))


def test_results_builder() -> None:
    contents = DesignQuantstudioReader(
        {
            "Results": get_results_sheet(),
            "Standard Curve Result": get_standard_curve_result_sheet(),
        },
    )

    target_dna_description = "RNaseP"
    well_item_id = 1
    data = StandardCurveWellList.get_well_result_data(contents)
    well_data = data[pd.Series(data.get("Well")) == 1]
    target_well_data = well_data[
        pd.Series(well_data.get("Target")) == target_dna_description
    ]
    target_data = SeriesData(
        pd.Series(target_well_data.iloc[0], index=target_well_data.columns)
    )
    result = Result.create(target_data, well_item_id)

    assert isinstance(result, Result)
    assert result.automatic_baseline_determination_enabled_setting is True
    assert result.automatic_cycle_threshold_enabled_setting is False
    assert result.baseline_corrected_reporter_result is None
    assert result.baseline_determination_end_cycle_setting == 22.0
    assert result.baseline_determination_start_cycle_setting == 3.0
    assert result.ct_mean == 28.34205318
    assert result.ct_sd == 0.1726292481
    assert result.cycle_threshold_result == 28.03761726
    assert result.cycle_threshold_value_setting == 0.1
    assert result.delta_ct_mean is None
    assert result.delta_ct_se is None
    assert result.delta_delta_ct is None
    assert result.efficiency == 99.17472224
    assert result.genotyping_determination_method_setting is None
    assert result.genotyping_determination_result is None
    assert result.normalized_reporter_result is None
    assert result.quantity == 6455.402377
    assert result.quantity_mean == 5271.394763
    assert result.quantity_sd == 666.3027554
    assert result.r_squared == 0.9880202381
    assert result.rn_mean is None
    assert result.rn_sd is None
    assert result.rq is None
    assert result.rq_max is None
    assert result.rq_min is None
    assert result.slope == -3.3419
    assert result.y_intercept == 40.77


def get_standard_curve_result_sheet() -> pd.DataFrame:
    header = pd.DataFrame(
        [
            ["File Name", "file.xlsx"],
            [None, None],
        ]
    )

    raw_data = [
        ("Well", 1),
        ("Well Position", "A1"),
        ("Sample", "Unk_5K"),
        ("Quantity", 6455.402377),
        ("Target", "RNaseP"),
        ("Dye", "FAM"),
        ("Task", "UNKNOWN"),
        ("Reporter", "FAM"),
        ("Quencher", "NFQ-MGB"),
        ("Amp Status", "AMP"),
        ("Cq", 28.03761726),
        ("Cq Mean", 28.34205318),
        ("Cq Confidence", 0.9780058625),
        ("Cq SD", 0.1726292481),
        ("Quantity Mean", 5271.394763),
        ("Quantity SD", 666.3027554),
        ("Auto Threshold", "FALSE"),
        ("Threshold", 0.1),
        ("Auto Baseline", "TRUE"),
        ("Baseline Start", 3),
        ("Baseline End", 22),
        ("Tm1", None),
        ("Tm2", None),
        ("Tm3", None),
        ("Tm4", None),
        ("Y-Intercept", 40.77),
        ("R2", 0.9880202381),
        ("Slope", -3.3419),
        ("Efficiency", 99.17472224),
        ("Standard Deviation", 0.1651328326),
        ("Standard Error", 0.08673485617),
        ("Omit", "FALSE"),
    ]

    data = pd.DataFrame(
        [
            [title for title, _ in raw_data],
            [value for _, value in raw_data],
        ]
    )

    return pd.concat([header, data])


def get_results_sheet() -> pd.DataFrame:
    header = pd.DataFrame(
        [
            ["File Name", "file.xlsx"],
            [None, None],
        ]
    )

    raw_data = [
        ("Well", 1),
        ("Well Position", "A1"),
        ("Omit", False),
        ("Sample", "Unk_5K"),
        ("Target", "RNaseP"),
        ("Task", "UNKNOWN"),
        ("Reporter", "FAM"),
        ("Quencher", "NFQ-MGB"),
        ("Amp Status", "AMP"),
        ("Amp Score", 1.280378),
        ("Curve Quality", None),
        ("Result Quality Issues", None),
        ("Cq", 28.037617),
        ("Cq Confidence", 0.978006),
        ("Cq Mean", 28.342053),
        ("Cq SD", 0.172629),
        ("Auto Threshold", False),
        ("Threshold", 0.1),
        ("Auto Baseline", True),
        ("Baseline Start", 3),
        ("Baseline End", 22),
    ]

    data = pd.DataFrame(
        [
            [title for title, _ in raw_data],
            [value for _, value in raw_data],
        ]
    )

    return pd.concat([header, data])


def get_raw_header_contents(
    measurement_time: str | None = "2010-10-01 01:44:54 AM EDT",
    plate_well_count: str | None = "96-Well 0.2-mL Block",
    device_identifier: str | None = "QS1-Eng2",
    model_number: str | None = "QuantStudio(TM) 6 Flex System",
    device_serial_number: str | None = "278880034",
    measurement_method_identifier: str | None = "Ct",
    pcr_detection_chemistry: str | None = "TAQMAN",
    passive_reference_dye_setting: str | None = "ROX",
    barcode: str | None = None,
    analyst: str | None = None,
    experimental_data_identifier: None
    | (str) = "QuantStudio 96-Well Presence-Absence Example",
    pcr_stage_number: str | None = "Stage 2 Step 2",
    software_name_and_version: str | None = "Design & Analysis Software v2.7.0",
    block_serial_number: str | None = "1",
    heated_cover_serial_number: str | None = "2",
) -> SeriesData:
    return SeriesData(
        pd.Series(
            {
                "Run End Data/Time": measurement_time,
                "Block Type": plate_well_count,
                "Instrument Name": device_identifier,
                "Instrument Type": model_number,
                "Instrument Serial Number": device_serial_number,
                "Quantification Cycle Method": measurement_method_identifier,
                "Chemistry": pcr_detection_chemistry,
                "Passive Reference": passive_reference_dye_setting,
                "Barcode": barcode,
                "Operator": analyst,
                "File Name": experimental_data_identifier,
                "PCR Stage/Step Number": pcr_stage_number,
                "Software Name and Version": software_name_and_version,
                "Block Serial Number": block_serial_number,
                "Heated Cover Serial Number": heated_cover_serial_number,
            }
        )
    )
