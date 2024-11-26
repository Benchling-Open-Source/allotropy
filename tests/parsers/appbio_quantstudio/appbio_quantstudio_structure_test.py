from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_reader import (
    AppBioQuantStudioReader,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    Header,
    Result,
)
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.types import IOType

TESTDATA = Path(Path(__file__).parent, "testdata")


def _read_to_lines(io_: IOType, encoding: str | None = None) -> list[str]:
    named_file_contents = NamedFileContents(io_, "test.csv", encoding=encoding)
    return read_to_lines(named_file_contents)


def test_header_builder_returns_header_instance() -> None:
    assert isinstance(Header.create(get_reader().header), Header)


def test_header_builder() -> None:
    device_identifier = "device1"
    model_number = "123"
    device_serial_number = "1234"
    measurement_method_identifier = "measurement ID"
    pcr_detection_chemistry = "detection1"
    passive_reference_dye_setting = "blue"
    experimental_data_identifier = "data Identifier"

    reader = get_reader(
        measurement_time="2010-10-01 01:44:54 AM EDT",
        plate_well_count="96 plates",
        experiment_type="Genotyping",
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        pcr_detection_chemistry=pcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        experimental_data_identifier=experimental_data_identifier,
    )

    assert Header.create(reader.header) == Header(
        measurement_time="2010-10-01 01:44:54 AM EDT",
        plate_well_count=96,
        experiment_type=ExperimentType.genotyping_qPCR_experiment,
        device_identifier=device_identifier,
        model_number=model_number,
        device_serial_number=device_serial_number,
        measurement_method_identifier=measurement_method_identifier,
        pcr_detection_chemistry=pcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        barcode=None,
        analyst=None,
        experimental_data_identifier=experimental_data_identifier,
    )


@pytest.mark.parametrize(
    "parameter,expected_error",
    [
        ("model_number", "Expected non-null value for Instrument Type."),
        (
            "measurement_method_identifier",
            "Expected non-null value for Quantification Cycle Method.",
        ),
    ],
)
def test_header_builder_required_parameter_none_then_raise(
    parameter: str, expected_error: str
) -> None:
    reader = get_reader(**{parameter: None})
    with pytest.raises(AllotropeConversionError, match=expected_error):
        Header.create(reader.header)


def test_header_builder_plate_well_count() -> None:
    header = Header.create(get_reader(plate_well_count="96 plates").header)
    assert header.plate_well_count == 96

    header = Header.create(get_reader(plate_well_count="Fast 96 plates").header)
    assert header.plate_well_count == 96

    header = Header.create(get_reader(plate_well_count="384 plates").header)
    assert header.plate_well_count == 384

    header = Header.create(get_reader(plate_well_count="Fast 384 plates").header)
    assert header.plate_well_count == 384

    header = Header.create(get_reader(plate_well_count="200 plates").header)
    assert header.plate_well_count is None

    header = Header.create(get_reader(plate_well_count="0 plates").header)
    assert header.plate_well_count is None


def test_results_builder() -> None:

    data = pd.DataFrame(
        {
            "Well": [1],
            "SNP Assay Name": ["CYP19_2"],
            "Allele1 Automatic Ct Threshold": [True],
            "Allele1 Ct Threshold": [0.219],
            "Allele2 Ct Threshold": [9999],
            "Allele1 Ct": ["Undetermined"],
        }
    )
    result = Result.create_results(data, ExperimentType.genotyping_qPCR_experiment)[1][
        "CYP19_2-Allele1"
    ]
    assert isinstance(result, Result)
    assert result.cycle_threshold_value_setting == 0.219
    assert result.cycle_threshold_result is None
    assert result.automatic_cycle_threshold_enabled_setting is True


def get_reader(
    raw_text: str | None = None,
    measurement_time: str | None = "2010-10-01 01:44:54 AM EDT",
    plate_well_count: str | None = "96-Well Block (0.2mL)",
    experiment_type: str | None = "Presence/Absence",
    device_identifier: str | None = "278880034",
    model_number: str | None = "QuantStudio(TM) 6 Flex System",
    device_serial_number: str | None = "278880034",
    measurement_method_identifier: str | None = "Ct",
    pcr_detection_chemistry: str | None = "TAQMAN",
    passive_reference_dye_setting: str | None = "ROX",
    barcode: str | None = "NA",
    analyst: str | None = "NA",
    experimental_data_identifier: None
    | (str) = "QuantStudio 96-Well Presence-Absence Example",
) -> AppBioQuantStudioReader:
    if raw_text is None:
        header_dict = {
            "Experiment Run End Time": measurement_time,
            "Block Type": plate_well_count,
            "Experiment Type ": experiment_type,
            "Instrument Name": device_identifier,
            "Instrument Type": model_number,
            "Instrument Serial Number": device_serial_number,
            "Quantification Cycle Method": measurement_method_identifier,
            "Chemistry": pcr_detection_chemistry,
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

    return AppBioQuantStudioReader.create(
        NamedFileContents(
            contents=BytesIO(raw_text.encode("utf-8")), original_file_path="test.txt"
        )
    )
