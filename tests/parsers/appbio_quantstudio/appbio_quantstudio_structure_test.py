from __future__ import annotations

from io import BytesIO
from typing import Optional

import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    Data,
    Header,
)
from allotropy.parsers.lines_reader import LinesReader
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import get_data, get_data2


def get_raw_header_contents(
    raw_text: Optional[str] = None,
    measurement_time: Optional[str] = "2010-10-01 01:44:54 AM EDT",
    plate_well_count: Optional[str] = "96-Well Block (0.2mL)",
    experiment_type: Optional[str] = "Presence/Absence",
    device_identifier: Optional[str] = "278880034",
    model_number: Optional[str] = "QuantStudio(TM) 6 Flex System",
    device_serial_number: Optional[str] = "278880034",
    measurement_method_identifier: Optional[str] = "Ct",
    qpcr_detection_chemistry: Optional[str] = "TAQMAN",
    passive_reference_dye_setting: Optional[str] = "ROX",
    barcode: Optional[str] = "NA",
    analyst: Optional[str] = "NA",
    experimental_data_identifier: Optional[
        str
    ] = "QuantStudio 96-Well Presence-Absence Example",
) -> BytesIO:
    if raw_text is not None:
        return BytesIO(raw_text.encode("utf-8"))

    header_dict = {
        "Experiment Run End Time": measurement_time,
        "Block Type": plate_well_count,
        "Experiment Type ": experiment_type,
        "Instrument Name": device_identifier,
        "Instrument Type": model_number,
        "Instrument Serial Number": device_serial_number,
        "Quantification Cycle Method": measurement_method_identifier,
        "Chemistry": qpcr_detection_chemistry,
        "Passive Reference": passive_reference_dye_setting,
        "Experiment Barcode": barcode,
        "Experiment User Name": analyst,
        "Experiment Name": experimental_data_identifier,
    }

    raw_text = "\n".join(
        [
            f"* {header_name} = {header_value}"
            for header_name, header_value in header_dict.items()
            if header_value is not None
        ]
    )

    return BytesIO(raw_text.encode("utf-8"))


def test_create_header() -> None:
    device_identifier = "device1"
    model_number = "123"
    device_serial_number = "1234"
    measurement_method_identifier = "measurement ID"
    qpcr_detection_chemistry = "detection1"
    passive_reference_dye_setting = "blue"
    experimental_data_identifier = "data Identifier"

    header_contents = get_raw_header_contents(
        measurement_time="2010-10-01 01:44:54 AM EDT",
        plate_well_count="96 plates",
        experiment_type="Genotyping",
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        qpcr_detection_chemistry=qpcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        experimental_data_identifier=experimental_data_identifier,
    )

    assert Header.create(LinesReader(header_contents)) == Header(
        measurement_time="2010-10-01 01:44:54",
        plate_well_count=96,
        experiment_type=ExperimentType.genotyping_qPCR_experiment,
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        qpcr_detection_chemistry=qpcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        barcode=None,
        analyst=None,
        experimental_data_identifier=experimental_data_identifier,
    )


@pytest.mark.parametrize(
    "parameter",
    [
        "device_identifier",
        "model_number",
        "device_serial_number",
        "measurement_method_identifier",
        "qpcr_detection_chemistry",
        "plate_well_count",
    ],
)
@pytest.mark.short
def test_create_header_required_parameter_none_then_raise(parameter: str) -> None:
    header_contents = get_raw_header_contents(**{parameter: None})

    with pytest.raises(AllotropeConversionError, match="Expected non-null value"):
        Header.create(LinesReader(header_contents))


@pytest.mark.short
def test_create_header_invalid_plate_well_count() -> None:
    header_contents = get_raw_header_contents(plate_well_count="0 plates")

    with pytest.raises(AllotropeConversionError):
        Header.create(LinesReader(header_contents))


@pytest.mark.short
def test_create_header_no_header_then_raise() -> None:
    header_contents = get_raw_header_contents(raw_text="")

    with pytest.raises(AllotropeConversionError):
        Header.create(LinesReader(header_contents))


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
