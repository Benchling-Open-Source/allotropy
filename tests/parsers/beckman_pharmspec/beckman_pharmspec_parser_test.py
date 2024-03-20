from pathlib import Path

import pytest

from allotropy.allotrope.models.light_obscuration_benchling_2023_12_light_obscuration import (
    LightObscurationAggregateDocument,
    MeasurementDocumentItem,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_pharmspec.pharmspec_parser import PharmSpecParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.to_allotrope import allotrope_from_file
from tests.parsers.test_utils import from_file, validate_contents

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
    assert (
        model.light_obscuration_aggregate_document.light_obscuration_document[
            0
        ].equipment_serial_number
        == "1808303021"
    )
    assert (
        model.light_obscuration_aggregate_document.light_obscuration_document[
            0
        ].sample_identifier
        == "ExampleTimepoint"
    )
    assert model.light_obscuration_aggregate_document.light_obscuration_document[
        0
    ].measurement_aggregate_document
    assert model.light_obscuration_aggregate_document.light_obscuration_document[
        0
    ].measurement_aggregate_document.measurement_document

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
        assert isinstance(elem.distribution_document, list)
        assert len(elem.distribution_document) == 1
        assert isinstance(elem.distribution_document[0].distribution, list)

        # 5 rows in the distribution document
        assert len(elem.distribution_document[0].distribution) == 5

        # Ensure correct order and particle sizes
        for i, particle_size in enumerate([2, 5, 10, 25, 50]):
            test = elem.distribution_document[0].distribution[i].particle_size
            assert test.value == particle_size


@pytest.mark.short
def test_asm(test_file: Path) -> None:
    asm = allotrope_from_file(str(test_file), VENDOR_TYPE)
    assert isinstance(asm, dict)


@pytest.mark.short
def test_parse_beckman_pharmspec_hiac_to_asm_contents(test_file: Path) -> None:
    expected_filepath = str(test_file.absolute()).replace(".xlsx", ".json")
    allotrope_dict = from_file(str(test_file.absolute()), VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
