from __future__ import annotations

from io import BytesIO
from typing import Optional

import pandas as pd
import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_builders import (
    DataBuilder,
    HeaderBuilder,
    ResultsBuilder,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    Data,
    Header,
    Result,
    WellItem,
)
from allotropy.parsers.appbio_quantstudio.calculated_document import CalculatedDocument
from allotropy.parsers.appbio_quantstudio.referenceable import Referenceable
from allotropy.parsers.lines_reader import LinesReader
from tests.parsers.appbio_quantstudio.appbio_quantstudio_data import (
    get_data,
    get_data2,
    get_genotyping_data,
    get_rel_std_curve_data,
)


def rm_uuid(data: Data) -> Data:
    for well in data.wells:
        if well.calculated_document:
            rm_uuid_calc_doc(well.calculated_document)

        for well_item in well.items.values():
            well_item.uuid = ""

    for calc_doc in data.calculated_documents:
        rm_uuid_calc_doc(calc_doc)

    return data


def rm_uuid_calc_doc(calc_doc: CalculatedDocument) -> None:
    calc_doc.uuid = ""
    for source in calc_doc.data_sources:
        if isinstance(source.reference, CalculatedDocument):
            rm_uuid_calc_doc(source.reference)
        elif isinstance(source.reference, Referenceable):
            source.reference.uuid = ""


@pytest.mark.short
def test_header_builder_returns_header_instance() -> None:
    header_contents = get_raw_header_contents()

    assert isinstance(HeaderBuilder.build(LinesReader(header_contents)), Header)


def test_header_builder() -> None:
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

    assert HeaderBuilder.build(LinesReader(header_contents)) == Header(
        measurement_time="2010-10-01 01:44:54 AM EDT",
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
    "parameter,expected_error",
    [
        ("device_identifier", "Unable to get device identifier"),
        ("model_number", "Unable to get model number"),
        ("device_serial_number", "Unable to get device serial number"),
        (
            "measurement_method_identifier",
            "Unable to get measurement method identifier",
        ),
        ("qpcr_detection_chemistry", "Unable to get qpcr detection chemistry"),
        ("plate_well_count", "Unable to interpret plate well count"),
    ],
)
@pytest.mark.short
def test_header_builder_required_parameter_none_then_raise(
    parameter: str, expected_error: str
) -> None:
    header_contents = get_raw_header_contents(**{parameter: None})

    with pytest.raises(AllotropeConversionError, match=expected_error):
        HeaderBuilder.build(LinesReader(header_contents))


@pytest.mark.short
def test_header_builder_invalid_plate_well_count() -> None:
    header_contents = get_raw_header_contents(plate_well_count="0 plates")

    with pytest.raises(AllotropeConversionError):
        HeaderBuilder.build(LinesReader(header_contents))


@pytest.mark.short
def test_header_builder_no_header_then_raise() -> None:
    header_contents = get_raw_header_contents(raw_text="")

    with pytest.raises(AllotropeConversionError):
        HeaderBuilder.build(LinesReader(header_contents))


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
    well_item = WellItem(
        uuid="be566c58-41f3-40f8-900b-ef1dff20d264",
        identifier=1,
        position="A1",
        target_dna_description="CYP19_2-Allele 1",
        sample_identifier="NTC",
        well_location_identifier="A1",
        reporter_dye_setting="SYBR",
        quencher_dye_setting=None,
        sample_role_type="PC_ALLELE_1",
    )
    result = ResultsBuilder.build(
        data, well_item, ExperimentType.genotyping_qPCR_experiment
    )
    assert isinstance(result, Result)
    assert result.cycle_threshold_value_setting == 0.219
    assert result.cycle_threshold_result is None
    assert result.automatic_cycle_threshold_enabled_setting is True


@pytest.mark.short
@pytest.mark.parametrize(
    "test_filepath,expected_data",
    [
        (
            "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test01.txt",
            get_data(),
        ),
        (
            "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test02.txt",
            get_data2(),
        ),
        (
            "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test03.txt",
            get_genotyping_data(),
        ),
        (
            "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_test04.txt",
            get_rel_std_curve_data(),
        ),
    ],
)
def test_data_builder(test_filepath: str, expected_data: Data) -> None:
    with open(test_filepath, "rb") as raw_contents:
        reader = LinesReader(raw_contents)
    assert rm_uuid(DataBuilder.build(reader)) == rm_uuid(expected_data)


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
