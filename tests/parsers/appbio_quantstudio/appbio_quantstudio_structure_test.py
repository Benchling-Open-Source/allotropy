from __future__ import annotations

from io import StringIO

import pandas as pd
import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Data,
    Header,
    Result,
    Well,
    WellItem,
)
from allotropy.parsers.lines_reader import LinesReader
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import get_data, get_data2


def get_reader_from_lines(lines: list[str]) -> LinesReader:
    reader = LinesReader(StringIO("\n".join(lines)))
    reader.read_csv_kwargs = {"header": None, "sep": ","}
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
def test_data_builder() -> None:
    test_filepath = (
        "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test01.txt"
    )
    with open(test_filepath, "rb") as raw_contents:
        reader = LinesReader(raw_contents)

    result = Data.create(reader)
    assert result == get_data()

    test_filepath = (
        "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test02.txt"
    )
    with open(test_filepath, "rb") as raw_contents:
        reader = LinesReader(raw_contents)

    result = Data.create(reader)
    assert result == get_data2()
