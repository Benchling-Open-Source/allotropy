from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_data,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    Header,
    Result,
)
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.types import IOType
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import (
    get_broken_calc_doc_data,
    get_data,
    get_data2,
    get_genotyping_data,
    get_rel_std_curve_data,
)

TESTDATA = Path(Path(__file__).parent, "testdata")


def rm_uuid(data: Data) -> Data:
    for measurement_group in data.measurement_groups:
        for measurement in measurement_group.measurements:
            measurement.identifier = ""

    for calc_doc in data.calculated_data.items:
        calc_doc.identifier = ""
        for source in calc_doc.data_sources:
            source.identifier = ""
    return data


def _read_to_lines(io_: IOType, encoding: str | None = None) -> list[str]:
    named_file_contents = NamedFileContents(io_, "test.csv", encoding=encoding)
    return read_to_lines(named_file_contents)


@pytest.mark.short
def test_header_builder_returns_header_instance() -> None:
    header_contents = get_raw_header_contents()

    lines = _read_to_lines(header_contents)
    assert isinstance(Header.create(LinesReader(lines)), Header)


def test_header_builder() -> None:
    device_identifier = "device1"
    model_number = "123"
    device_serial_number = "1234"
    measurement_method_identifier = "measurement ID"
    pcr_detection_chemistry = "detection1"
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
        pcr_detection_chemistry=pcr_detection_chemistry,
        passive_reference_dye_setting=passive_reference_dye_setting,
        experimental_data_identifier=experimental_data_identifier,
    )

    lines = _read_to_lines(header_contents)
    assert Header.create(LinesReader(lines)) == Header(
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


@pytest.mark.short
@pytest.mark.parametrize(
    "parameter,expected_error",
    [
        ("model_number", "Expected non-null value for Instrument Type."),
        (
            "measurement_method_identifier",
            "Expected non-null value for Quantification Cycle Method.",
        ),
        ("pcr_detection_chemistry", "Expected non-null value for Chemistry."),
    ],
)
def test_header_builder_required_parameter_none_then_raise(
    parameter: str, expected_error: str
) -> None:
    header_contents = get_raw_header_contents(**{parameter: None})
    lines = _read_to_lines(header_contents)
    lines_reader = LinesReader(lines)
    with pytest.raises(AllotropeConversionError, match=expected_error):
        Header.create(lines_reader)


@pytest.mark.short
def test_header_builder_plate_well_count() -> None:
    header_contents = get_raw_header_contents(plate_well_count="96 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count == 96

    header_contents = get_raw_header_contents(plate_well_count="Fast 96 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count == 96

    header_contents = get_raw_header_contents(plate_well_count="384 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count == 384

    header_contents = get_raw_header_contents(plate_well_count="Fast 384 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count == 384

    header_contents = get_raw_header_contents(plate_well_count="200 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count is None

    header_contents = get_raw_header_contents(plate_well_count="0 plates")
    lines = _read_to_lines(header_contents)
    header = Header.create(LinesReader(lines))
    assert header.plate_well_count is None


@pytest.mark.short
def test_header_builder_no_header_then_raise() -> None:
    header_contents = get_raw_header_contents(raw_text="")
    lines = _read_to_lines(header_contents, encoding="UTF-8")
    lines_reader = LinesReader(lines)
    with pytest.raises(
        AllotropeConversionError,
        match="Expected non-null value for Block Type.",
    ):
        Header.create(lines_reader)


@pytest.mark.short
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


@pytest.mark.short
@pytest.mark.parametrize(
    "test_filepath,create_expected_data_func",
    [
        (
            f"{TESTDATA}/exclude/appbio_quantstudio_test01.txt",
            get_data,
        ),
        (
            f"{TESTDATA}/exclude/appbio_quantstudio_test02.txt",
            get_data2,
        ),
        (
            f"{TESTDATA}/exclude/appbio_quantstudio_test03.txt",
            get_genotyping_data,
        ),
        (
            f"{TESTDATA}/exclude/appbio_quantstudio_test04.txt",
            get_rel_std_curve_data,
        ),
        (
            f"{TESTDATA}/exclude/appbio_quantstudio_test05.txt",
            get_broken_calc_doc_data,
        ),
    ],
)
def test_data_builder(
    test_filepath: str, create_expected_data_func: Callable[[str], Data]
) -> None:
    with open(test_filepath, "rb") as raw_contents:
        lines = _read_to_lines(raw_contents)
    reader = LinesReader(lines)
    assert rm_uuid(create_data(reader, test_filepath)) == rm_uuid(
        create_expected_data_func(test_filepath)
    )


def get_raw_header_contents(
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

    return BytesIO(raw_text.encode("utf-8"))
