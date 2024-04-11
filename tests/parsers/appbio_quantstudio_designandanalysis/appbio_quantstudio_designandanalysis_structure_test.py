from __future__ import annotations

from typing import Optional

import pandas as pd
import pytest

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Header,
    Result,
    WellItem,
)


@pytest.mark.design_quantstudio
def test_header_builder_returns_header_instance() -> None:
    header_contents = get_raw_header_contents()
    assert isinstance(Header.create(header_contents), Header)


@pytest.mark.design_quantstudio
def test_header_builder() -> None:
    measurement_time = "2010-10-01 01:44:54 AM EDT"
    device_identifier = "device1"
    model_number = "123"
    device_serial_number = "1234"
    measurement_method_identifier = "measurement ID"
    pcr_detection_chemistry = "detection1"
    passive_reference_dye_setting = "blue"
    experimental_data_identifier = "data Identifier"

    header_contents = get_raw_header_contents(
        measurement_time=measurement_time,
        plate_well_count="96 plates",
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
        experimental_data_identifier=experimental_data_identifier,
        pcr_stage_number=2,
        software_name="Design & Analysis Software",
        software_version="2.7.0",
        block_serial_number="1",
        heated_cover_serial_number="2",
    )


@pytest.mark.design_quantstudio
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


@pytest.mark.design_quantstudio
def test_header_builder_invalid_plate_well_count() -> None:
    header_contents = get_raw_header_contents(plate_well_count="0 plates")

    with pytest.raises(AllotropeConversionError):
        Header.create(header_contents)


@pytest.mark.design_quantstudio
def test_header_builder_no_header_then_raise() -> None:
    with pytest.raises(AllotropeConversionError):
        Header.create(pd.Series())


@pytest.mark.design_quantstudio
def test_results_builder() -> None:
    data = pd.DataFrame(
        {
            "Well": [1],
            "Well Position": ["A1"],
            "Omit": [False],
            "Sample": ["Unk_5K"],
            "Target": ["RNaseP"],
            "Task": ["UNKNOWN"],
            "Reporter": ["FAM"],
            "Quencher": ["NFQ-MGB"],
            "Amp Status": ["AMP"],
            "Amp Score": [1.280378],
            "Curve Quality": [None],
            "Result Quality Issues": [None],
            "Cq": [28.037617],
            "Cq Confidence": [0.978006],
            "Cq Mean": [28.342053],
            "Cq SD": [0.172629],
            "Auto Threshold": [False],
            "Threshold": [0.1],
            "Auto Baseline": [True],
            "Baseline Start": [3],
            "Baseline End": [22],
        }
    )
    well_item = WellItem(
        uuid="2b557369-c679-4a6f-b2cb-6b899ef9ab9d",
        identifier=1,
        target_dna_description="RNaseP",
        sample_identifier="Unk_5K",
        reporter_dye_setting="FAM",
        well_location_identifier="A1",
        quencher_dye_setting="NFQ-MGB",
        sample_role_type="UNKNOWN",
    )
    result = Result.create(
        data, well_item, ExperimentType.standard_curve_qPCR_experiment
    )
    assert isinstance(result, Result)
    assert result.cycle_threshold_value_setting == 0.1
    assert result.cycle_threshold_result == 28.037617
    assert result.automatic_cycle_threshold_enabled_setting is False
    assert result.automatic_baseline_determination_enabled_setting is True
    assert result.normalized_reporter_result is None
    assert result.baseline_corrected_reporter_result is None
    assert result.genotyping_determination_result is None
    assert result.genotyping_determination_method_setting is None
    assert result.quantity is None
    assert result.quantity_mean is None
    assert result.quantity_sd is None
    assert result.ct_mean == 28.342053
    assert result.ct_sd == 0.172629
    assert result.delta_ct_mean is None
    assert result.delta_ct_se is None
    assert result.delta_delta_ct is None
    assert result.rq is None
    assert result.rq_min is None
    assert result.rq_max is None
    assert result.rn_mean is None
    assert result.rn_sd is None
    assert result.y_intercept is None
    assert result.r_squared is None
    assert result.slope is None
    assert result.efficiency is None


def get_raw_header_contents(
    measurement_time: Optional[str] = "2010-10-01 01:44:54 AM EDT",
    plate_well_count: Optional[str] = "96-Well 0.2-mL Block",
    device_identifier: Optional[str] = "QS1-Eng2",
    model_number: Optional[str] = "QuantStudio(TM) 6 Flex System",
    device_serial_number: Optional[str] = "278880034",
    measurement_method_identifier: Optional[str] = "Ct",
    pcr_detection_chemistry: Optional[str] = "TAQMAN",
    passive_reference_dye_setting: Optional[str] = "ROX",
    barcode: Optional[str] = None,
    analyst: Optional[str] = None,
    experimental_data_identifier: Optional[
        str
    ] = "QuantStudio 96-Well Presence-Absence Example",
    pcr_stage_number: Optional[str] = "Stage 2 Step 2",
    software_name_and_version: Optional[str] = "Design & Analysis Software v2.7.0",
    block_serial_number: Optional[str] = "1",
    heated_cover_serial_number: Optional[str] = "2",
) -> pd.Series[str]:
    return pd.Series(
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
            "Experiment Name": experimental_data_identifier,
            "PCR Stage/Step Number": pcr_stage_number,
            "Software Name and Version": software_name_and_version,
            "Block Serial Number": block_serial_number,
            "Heated Cover Serial Number": heated_cover_serial_number,
        }
    )
