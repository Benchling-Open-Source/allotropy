import pytest

from allotropy.allotrope.models.light_obscuration_benchling_2023_12_light_obscuration import (
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
from allotropy.to_allotrope import allotrope_from_file

VENDOR_TYPE = Vendor.BECKMAN_PHARMSPEC

OUTPUT_FILES = (
    "hiac_example_1",
    "hiac_example_2",
    "hiac_example_3",
    "hiac_example_4",
    "hiac_example_5",
)

TEST_DATA_DIR = "tests/parsers/beckman_pharmspec/testdata/"


def _get_test_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}.xlsx"


def _get_expected_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}.json"


@pytest.mark.short
@pytest.mark.parametrize(
    "file_name,num_measurement_docs,has_calculated_doc",
    [
        (OUTPUT_FILES[0], 2, True),
        (OUTPUT_FILES[1], 3, True),
        (OUTPUT_FILES[2], 1, True),
        (OUTPUT_FILES[3], 1, False),
        (OUTPUT_FILES[4], 3, False),
    ],
)
def test_get_model(
    file_name: str, num_measurement_docs: int, *, has_calculated_doc: bool
) -> None:
    test_file = _get_test_file_path(file_name)
    parser = PharmSpecParser(TimestampParser())

    model = parser.to_allotrope(NamedFileContents(open(test_file, "rb"), ""))
    assert isinstance(
        model.light_obscuration_aggregate_document,
        LightObscurationAggregateDocument,
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

    assert (
        len(
            model.light_obscuration_aggregate_document.light_obscuration_document[
                0
            ].measurement_aggregate_document.measurement_document
        )
        == num_measurement_docs
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

    if has_calculated_doc:
        assert (
            model.light_obscuration_aggregate_document.calculated_data_aggregate_document
        )
    else:
        assert (
            not model.light_obscuration_aggregate_document.calculated_data_aggregate_document
        )


@pytest.mark.short
@pytest.mark.parametrize("file_name", OUTPUT_FILES)
def test_asm(file_name: str) -> None:
    test_file = _get_test_file_path(file_name)
    asm = allotrope_from_file(str(test_file), VENDOR_TYPE)
    assert isinstance(asm, dict)


@pytest.mark.short
@pytest.mark.parametrize("file_name", OUTPUT_FILES)
def test_parse_beckman_pharmspec_hiac_to_asm_contents(file_name: str) -> None:
    test_file = _get_test_file_path(file_name)
    expected_filepath = _get_expected_file_path(file_name)
    allotrope_dict = from_file(test_file, VENDOR_TYPE)
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
