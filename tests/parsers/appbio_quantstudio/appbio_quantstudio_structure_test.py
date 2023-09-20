from __future__ import annotations

from io import StringIO

import pandas as pd
import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    create_wells,
    Data,
    GenotypingWell,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    Result,
    Well,
    WellItem,
)
from allotropy.parsers.lines_reader import CSVBlockLinesReader
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import get_data, get_data2


def get_reader_from_lines(lines: list[str]) -> CSVBlockLinesReader:
    reader = CSVBlockLinesReader(StringIO("\n".join(lines)))
    reader.default_read_csv_kwargs = {"sep": "\t"}
    return reader


HEADER_LINES = [
    "* Experiment Run End Time = 2010-10-01 01:44:54 AM EDT",
    "* Block Type = 96 plates",
    "* Experiment Type = Genotyping",
    "* Instrument Name = device1",
    "* Instrument Type = 123",
    "* Instrument Serial Number = 1234",
    "* Quantification Cycle Method = measurement ID",
    "* Chemistry = detection1",
    "* Passive Reference = blue",
    "* Experiment Barcode = NA",
    "* Experiment User Name = NA",
    "* Experiment Name = QuantStudio 96-Well Presence-Absence Example",
]


def test_create_header() -> None:
    reader = get_reader_from_lines(HEADER_LINES)

    assert Header.create(reader) == Header(
        measurement_time="2010-10-01 01:44:54",
        plate_well_count=96,
        experiment_type=ExperimentType.genotyping_qPCR_experiment,
        device_identifier="device1",
        model_number="123",
        device_serial_number="1234",
        measurement_method_identifier="measurement ID",
        qpcr_detection_chemistry="detection1",
        passive_reference_dye_setting="blue",
        barcode=None,
        analyst=None,
        experimental_data_identifier="QuantStudio 96-Well Presence-Absence Example",
    )


@pytest.mark.parametrize(
    "parameter",
    [
        "Instrument Name",
        "Instrument Type",
        "Serial Number",
        "Cycle Method",
        "Chemistry",
        "Block Type",
    ],
)
@pytest.mark.short
def test_create_header_required_parameter_none_then_raise(parameter: str) -> None:
    with pytest.raises(AllotropeConversionError, match="Expected non-null value"):
        Header.create(
            get_reader_from_lines(
                [line for line in HEADER_LINES if parameter not in line]
            )
        )


@pytest.mark.short
def test_create_header_invalid_plate_well_count() -> None:
    lines = [
        "* Experiment Run End Time = 2010-10-01 01:44:54 AM EDT",
        "* Block Type = 0 plates",
    ]

    with pytest.raises(
        AllotropeConversionError, match="Block Type has invalid number prefix"
    ):
        Header.create(get_reader_from_lines(lines))


@pytest.mark.short
def test_create_header_no_header_then_raise() -> None:
    with pytest.raises(AllotropeConversionError):
        Header.create(get_reader_from_lines([""]))


WELL_ITEM_DICT = {
    "Well": "1",
    "Target Name": "TARGET_1",
    "Sample Name": "sample 1",
    "Reporter": "DYE",
    "Well Position": "A1",
    "Quencher": "THE_QUENCH",
    "Task": "sample role 1",
}


@pytest.mark.short
def test_create_well_item() -> None:
    series = pd.Series(WELL_ITEM_DICT)
    assert WellItem.create(series) == WellItem(
        identifier=1,
        target_dna_description="TARGET_1",
        sample_identifier="sample 1",
        reporter_dye_setting="DYE",
        position="A1",
        well_location_identifier="A1",
        quencher_dye_setting="THE_QUENCH",
        sample_role_type="sample role 1",
    )


@pytest.mark.short
def test_create_well_item_optional_values() -> None:
    series = pd.Series(
        {
            "Well": "2",
            "Sample Name": "sample 2",
        }
    )
    assert WellItem.create(series, "TARGET_2") == WellItem(
        identifier=2,
        target_dna_description="TARGET_2",
        sample_identifier="sample 2",
        position="UNDEFINED",
    )


@pytest.mark.parametrize("parameter", ["Well", "Target Name", "Sample Name"])
@pytest.mark.short
def test_create_well_item_required_parameter_none_then_raise(parameter: str) -> None:
    with pytest.raises(AllotropeConversionError, match="Expected non-null value"):
        WellItem.create(
            pd.Series({k: v for k, v in WELL_ITEM_DICT.items() if parameter not in k})
        )


@pytest.mark.short
def test_well_item_fails_if_access_unset_required_param() -> None:
    well_item = WellItem.create(pd.Series(WELL_ITEM_DICT))
    with pytest.raises(AllotropeConversionError):
        assert well_item.amplification_data

    well_item.amplification_data = AmplificationData(1.1, [], [], [])
    assert well_item.amplification_data.total_cycle_number_setting == 1.1

    with pytest.raises(AllotropeConversionError):
        assert well_item.result

    well_item.result = Result(1.0)
    assert well_item.result.cycle_threshold_value_setting == 1.0


@pytest.mark.short
def test_create_well() -> None:
    data = pd.DataFrame(
        {
            "Well": ["1", "1"],
            "Target Name": ["T1", "T2"],
            "Sample Name": ["S1", "S2"],
            "Reporter": [None, "ME"],
            "Quencher": ["QUNCH", ""],
        }
    )
    well = Well.create(1, data)

    assert well.identifier == 1
    assert len(well.items) == 2
    assert well.items[0].identifier == 1
    assert well.items[0].target_dna_description == "T1"
    assert well.items[0].sample_identifier == "S1"
    assert not well.items[0].reporter_dye_setting
    assert well.items[0].quencher_dye_setting == "QUNCH"
    assert well.items[1].identifier == 1
    assert well.items[1].target_dna_description == "T2"
    assert well.items[1].sample_identifier == "S2"
    assert well.items[1].reporter_dye_setting == "ME"
    assert not well.items[1].quencher_dye_setting


@pytest.mark.short
def test_create_genotyping_well() -> None:
    data = pd.DataFrame(
        {
            "Well": ["1"],
            "Sample Name": ["S1"],
            "SNP Assay Name": ["ASSAY_1"],
            "Allele1 Name": ["AL1"],
            "Allele2 Name": ["AL2"],
        }
    )
    well = GenotypingWell.create(1, data)

    assert well.identifier == 1
    assert len(well.items) == 2
    assert well.items[0].identifier == 1
    assert well.items[0].target_dna_description == "ASSAY_1-AL1"
    assert well.items[0].sample_identifier == "S1"
    assert well.items[1].identifier == 1
    assert well.items[1].target_dna_description == "ASSAY_1-AL2"
    assert well.items[1].sample_identifier == "S1"


@pytest.mark.short
def test_create_wells() -> None:
    reader = get_reader_from_lines(
        [
            "[Sample Setup]",
            "Well	Well Position	Sample Name	Target Name",
            "1	A1	S1	T1",
        ]
    )

    wells = create_wells(
        reader, experiment_type=ExperimentType.standard_curve_qPCR_experiment
    )
    assert len(wells) == 1
    well = wells[0]
    assert well.identifier == 1
    assert len(well.items) == 1
    assert well.items[0].identifier == 1
    assert well.items[0].target_dna_description == "T1"
    assert well.items[0].sample_identifier == "S1"


@pytest.mark.short
def test_create_genotyping_wells() -> None:
    reader = get_reader_from_lines(
        [
            "[Sample Setup]",
            "Well	Well Position	Sample Name	SNP Assay Name	Allele1 Name	Allele2 Name",
            "1	A1	S1	ASSAY_1	AL1	AL2",
        ]
    )

    wells = create_wells(
        reader, experiment_type=ExperimentType.genotyping_qPCR_experiment
    )
    assert len(wells) == 1
    well = wells[0]
    assert well.identifier == 1
    assert len(well.items) == 2
    assert well.items[0].identifier == 1
    assert well.items[0].target_dna_description == "ASSAY_1-AL1"
    assert well.items[0].sample_identifier == "S1"
    assert well.items[1].identifier == 1
    assert well.items[1].target_dna_description == "ASSAY_1-AL2"
    assert well.items[1].sample_identifier == "S1"


@pytest.mark.short
def test_create_amplification_data() -> None:
    reader = get_reader_from_lines(
        [
            "[Amplification Data]",
            "Well	Cycle	Target Name	Rn	Delta Rn",
            "1	1	TARGET_1.1	1.1	1.111",
            "1	2	TARGET_1.1	1.12	-1.112",
            "1	1	TARGET_1.2	2.1	-2.2",
            "3	1	TARGET_3.1	3.12	-3",
        ]
    )
    assert AmplificationData.map_data(reader) == {
        1: {
            "TARGET_1.1": AmplificationData(2, [1, 2], [1.1, 1.12], [1.111, -1.112]),
            "TARGET_1.2": AmplificationData(1, [1], [2.1], [-2.2]),
        },
        3: {
            "TARGET_3.1": AmplificationData(1, [1], [3.12], [-3.0]),
        },
    }


@pytest.mark.short
def test_create_multicomponent_data() -> None:
    reader = get_reader_from_lines(
        [
            "[Multicomponent Data]",
            "Well	Well Position	Cycle	ROX	SYBR",
            "1	      A1	1	111.11	222.22",
            "1	      A1	2	333.33	444.44",
            "2	      A2	3	55,555.555	66,666.666",
        ]
    )
    assert MulticomponentData.map_data(reader) == {
        1: MulticomponentData(
            cycle=[1, 2], columns={"ROX": [111.11, 333.33], "SYBR": [222.22, 444.44]}
        ),
        2: MulticomponentData(
            cycle=[3], columns={"ROX": [55555.555], "SYBR": [66666.666]}
        ),
    }


@pytest.mark.short
def test_create_results() -> None:
    reader = get_reader_from_lines(
        [
            "[Results]",
            "Well	Target Name	CT	Automatic Ct Threshold	Ct Threshold	Automatic Baseline	Rn	Delta Rn	Call	Threshold Value	Baseline Start",
            "1	TARGET_1	1.0	false	2.0	true					1",
            "1	TARGET_2	0.3	true	0.4	false					1",
            "2	TARGET_1	500	true	600	true	100	200	200	200	1",
        ]
    )
    assert Result.map_data(
        reader, experiment_type=ExperimentType.standard_curve_qPCR_experiment
    ) == {
        1: {
            "TARGET_1": Result(
                cycle_threshold_value_setting=2.0,
                cycle_threshold_result=1.0,
                automatic_cycle_threshold_enabled_setting=False,
                automatic_baseline_determination_enabled_setting=True,
            ),
            "TARGET_2": Result(
                cycle_threshold_value_setting=0.4,
                cycle_threshold_result=0.3,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=False,
            ),
        },
        2: {
            "TARGET_1": Result(
                cycle_threshold_value_setting=600.0,
                cycle_threshold_result=500.0,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=100.0,
                baseline_corrected_reporter_result=200.0,
                genotyping_determination_result="200.0",
                genotyping_determination_method_setting=200.0,
            )
        },
    }


@pytest.mark.short
def test_create_genotyping_results() -> None:
    reader = get_reader_from_lines(
        [
            "[Results]",
            "Well	SNP Assay Name	Allele1 Name	Allele2 Name	AL1 Ct	AL2 Ct	AL1 Automatic Ct Threshold	AL1 Ct Threshold	AL2 Ct Threshold	AL2 Automatic Baseline	Rn	AL2 Delta Rn	Call	Threshold Value	Baseline Start",
            "1	ASSAY_1	AL1	AL2	1.0	2.0	false	20.0	21.0	true	0.01	0.001			1",
        ]
    )
    result = Result.map_data(
        reader, experiment_type=ExperimentType.genotyping_qPCR_experiment
    )
    expected = {
        1: {
            "ASSAY_1-AL1": Result(
                cycle_threshold_value_setting=20.0,
                cycle_threshold_result=1.0,
                automatic_cycle_threshold_enabled_setting=False,
                automatic_baseline_determination_enabled_setting=None,
                normalized_reporter_result=0.01,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
            ),
            "ASSAY_1-AL2": Result(
                cycle_threshold_value_setting=21.0,
                cycle_threshold_result=2.0,
                automatic_cycle_threshold_enabled_setting=None,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=0.01,
                baseline_corrected_reporter_result=0.001,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
            ),
        }
    }
    assert result == expected


@pytest.mark.short
def test_create_melt_curve_raw_data() -> None:
    reader = get_reader_from_lines(
        [
            "[Melt Curve Raw Data]",
            "Well	Well Position	Reading	Temperature	Fluorescence	Derivative",
            "1	A1	1	60.403	1.1	0.1",
            "1	A1	2	60.403	2.2	0.2",
            "2	A1	1	60.403	3.3	0.3",
        ]
    )
    assert MeltCurveRawData.map_data(reader) == {
        1: MeltCurveRawData(
            reading=[1, 2], fluorescence=[1.1, 2.2], derivative=[0.1, 0.2]
        ),
        2: MeltCurveRawData(reading=[1], fluorescence=[3.3], derivative=[0.3]),
    }


@pytest.mark.short
def test_data_builder() -> None:
    test_filepath = (
        "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test01.txt"
    )
    with open(test_filepath) as raw_contents:
        reader = get_reader_from_lines(raw_contents.read().split("\n"))

    result = Data.create(reader)
    assert result == get_data()

    test_filepath = (
        "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test02.txt"
    )
    with open(test_filepath) as raw_contents:
        reader = get_reader_from_lines(raw_contents.read().split("\n"))

    result = Data.create(reader)
    assert result == get_data2()
