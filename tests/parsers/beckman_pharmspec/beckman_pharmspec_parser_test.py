from pathlib import Path

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


@pytest.fixture()
def test_file_1() -> Path:
    """Test file 1 has two runs and an average distribution.

    :return: Path to test file 1
    """
    f = Path(__file__).parent / "testdata/hiac_example_1.xlsx"
    return f.absolute()


@pytest.fixture()
def test_file_2() -> Path:
    """Test file 2 has 3 runs and an average distribution.

    :return: Path to test file 2
    """
    f = Path(__file__).parent / "testdata/hiac_example_2.xlsx"
    return f.absolute()


@pytest.fixture()
def test_file_3() -> Path:
    """Test file 3 has 1 run and an average distribution.

    :return: Path to test file 3
    """
    f = Path(__file__).parent / "testdata/hiac_example_3.xlsx"
    return f.absolute()


@pytest.fixture()
def test_file_4() -> Path:
    """Test file 4 has 1 run and no calculated distribution.

    :return: Path to test file 4
    """
    f = Path(__file__).parent / "testdata/hiac_example_4.xlsx"
    return f.absolute()


@pytest.fixture()
def test_file_5() -> Path:
    """Test file 5 has 3 runs and no calculated distribution.

    :return: Path to test file 5
    """
    f = Path(__file__).parent / "testdata/hiac_example_5.xlsx"
    return f.absolute()


@pytest.fixture()
def test_files(
    test_file_1, test_file_2, test_file_3, test_file_4, test_file_5
) -> dict[str, Path]:
    return {
        "test_file_1": test_file_1,
        "test_file_2": test_file_2,
        "test_file_3": test_file_3,
        "test_file_4": test_file_4,
        "test_file_5": test_file_5,
    }


@pytest.mark.short
def test_get_model(test_files) -> None:
    tests = {
        "num_measurement_docs": {
            "test_file_1": 2,
            "test_file_2": 3,
            "test_file_3": 1,
            "test_file_4": 1,
            "test_file_5": 3,
        },
        "has_calculated_doc": {
            "test_file_1": True,
            "test_file_2": True,
            "test_file_3": True,
            "test_file_4": False,
            "test_file_5": False,
        }

    }
    for name, test_file in test_files.items():
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
            == tests["num_measurement_docs"][name]
        )
        for (
            elem
        ) in model.light_obscuration_aggregate_document.light_obscuration_document[
            0
        ].measurement_aggregate_document.measurement_document:
            assert isinstance(elem, MeasurementDocumentItem)
            assert isinstance(elem.measurement_identifier, str)
            assert isinstance(
                elem.processed_data_aggregate_document, ProcessedDataAggregateDocument
            )
            assert (
                len(elem.processed_data_aggregate_document.processed_data_document) == 1
            )
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

        if tests["has_calculated_doc"][name]:
            assert model.light_obscuration_aggregate_document.calculated_data_aggregate_document
        else:
            assert not model.light_obscuration_aggregate_document.calculated_data_aggregate_document


@pytest.mark.short
def test_asm(test_files) -> None:
    for _, test_file in test_files.items():
        asm = allotrope_from_file(str(test_file), VENDOR_TYPE)
        assert isinstance(asm, dict)


@pytest.mark.short
def test_parse_beckman_pharmspec_hiac_to_asm_contents(test_files) -> None:
    for _, test_file in test_files.items():
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
