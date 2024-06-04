from pathlib import Path

import pytest

from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    DeviceSystemDocument,
    DistributionAggregateDocument,
    DistributionItem,
    LightObscurationAggregateDocument,
    MeasurementDocumentItem,
    ProcessedDataAggregateDocument,
    SampleDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.testing.utils import from_file, validate_contents

VENDOR_TYPE = Vendor.BECKMAN_PHARMSPEC


@pytest.fixture()
def test_file() -> Path:
    f = Path(__file__).parent / "testdata/hiac_example_1.xlsx"
    return f.absolute()


@pytest.mark.short
def test_get_model(test_file: Path) -> None:
    parser = PharmSpecParser(TimestampParser())

    model = parser.to_allotrope(NamedFileContents(open(test_file, "rb"), ""))
    assert isinstance(
        model.light_obscuration_aggregate_document, LightObscurationAggregateDocument
    )
    assert isinstance(
        model.light_obscuration_aggregate_document.device_system_document,
        DeviceSystemDocument,
    )
    assert (
        model.light_obscuration_aggregate_document.device_system_document.equipment_serial_number
        == "1808303021"
    )

    assert (
        model.light_obscuration_aggregate_document.light_obscuration_document[
            0
        ].measurement_aggregate_document.measurement_document
        is not None
    )

    assert isinstance(
        model.light_obscuration_aggregate_document.light_obscuration_document[
            0
        ].measurement_aggregate_document.measurement_document[0],
        MeasurementDocumentItem,
    )

    assert isinstance(
        model.light_obscuration_aggregate_document.light_obscuration_document[0]
        .measurement_aggregate_document.measurement_document[0]
        .sample_document,
        SampleDocument,
    )

    assert (
        model.light_obscuration_aggregate_document.light_obscuration_document[0]
        .measurement_aggregate_document.measurement_document[0]
        .sample_document.sample_identifier
        == "ExampleTimepoint"
    )

    # # Single distribution document

    assert (
        len(
            model.light_obscuration_aggregate_document.light_obscuration_document[
                0
            ].measurement_aggregate_document.measurement_document
        )
        == 2
    )
    for elem in model.light_obscuration_aggregate_document.light_obscuration_document[
        0
    ].measurement_aggregate_document.measurement_document:
        assert isinstance(elem, MeasurementDocumentItem)
        assert isinstance(elem.measurement_identifier, str)
        assert isinstance(
            elem.processed_data_aggregate_document, ProcessedDataAggregateDocument
        )
        assert len(elem.processed_data_aggregate_document.processed_data_document) == 1
        assert isinstance(
            elem.processed_data_aggregate_document.processed_data_document[
                0
            ].distribution_aggregate_document,
            DistributionAggregateDocument,
        )
        assert (
            len(
                elem.processed_data_aggregate_document.processed_data_document[
                    0
                ].distribution_aggregate_document.distribution_document,
            )
            == 1
        )

        assert isinstance(
            elem.processed_data_aggregate_document.processed_data_document[0]
            .distribution_aggregate_document.distribution_document[0]
            .distribution[0],
            DistributionItem,
        )

        # 5 rows in the distribution document
        assert (
            len(
                elem.processed_data_aggregate_document.processed_data_document[0]
                .distribution_aggregate_document.distribution_document[0]
                .distribution
            )
            == 5
        )

        # Ensure correct order and particle sizes
        for i, particle_size in enumerate([2, 5, 10, 25, 50]):
            test = (
                elem.processed_data_aggregate_document.processed_data_document[0]
                .distribution_aggregate_document.distribution_document[0]
                .distribution[i]
                .particle_size
            )
            assert test.value == particle_size


@pytest.mark.short
def test_parse_beckman_pharmspec_hiac_to_asm_contents(test_file: Path) -> None:
    expected_filepath = str(test_file.absolute()).replace(".xlsx", ".json")
    allotrope_dict = from_file(str(test_file.absolute()), VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.short
def test_get_software_version_report_string() -> None:
    parser = PharmSpecParser(TimestampParser())
    tests = [
        ["HIAC PharmSpec v3.0 Summary Report", "3.0"],
        ["HIAC PharmSpec v3.0.1 Summary Report", "3.0.1"],
        ["HIAC PharmSpec v3 Summary Report", "3"],
        ["HIAC PharmSpec v Summary Report", "Unknown"],
        ["HIAC PharmSpec v3.0.10 Summary Report", "3.0.10"],
        ["HIAC PharmSpec v3.0.10.40 Summary Report", "3.0.10"],
    ]
    for t in tests:
        assert parser._get_software_version_report_string(t[0]) == t[1]
