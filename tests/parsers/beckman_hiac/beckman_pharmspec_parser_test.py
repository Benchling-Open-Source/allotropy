from pathlib import Path

import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_pharmspec.pharmspec_parser import PharmSpecParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.to_allotrope import allotrope_from_file
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

VENDOR_TYPE = Vendor.BECKMAN_PHARMSPEC


@pytest.fixture()
def test_file() -> Path:
    f = Path(__file__).parent / "testdata/hiac_example_1.xlsx"
    return f.absolute()


@pytest.mark.short
def test_get_model(test_file: Path) -> None:
    parser = PharmSpecParser(TimestampParser())
    model = parser._parse(open(test_file, "rb"), "")
    assert model.detector_identifier == "1808303021"
    assert model.sample_identifier == "ExampleTimepoint"
    assert model.measurement_document
    assert model.measurement_document.distribution_document

    # Single distribution document

    assert len(model.measurement_document.distribution_document) == 1

    # 5 rows in the distribution document
    assert isinstance(
        model.measurement_document.distribution_document[0].distribution, list
    )
    assert len(model.measurement_document.distribution_document[0].distribution) == 5

    # Ensure correct order and particle sizes
    for i, particle_size in enumerate([2, 5, 10, 25, 50]):
        test = (
            model.measurement_document.distribution_document[0]
            .distribution[i]
            .particle_size
        )
        assert test.value == particle_size


@pytest.mark.short
def test_asm(test_file: Path) -> None:
    asm = allotrope_from_file(str(test_file), Vendor.BECKMAN_PHARMSPEC)
    assert isinstance(asm, dict)


@pytest.mark.short
def test_parse_beckman_hiac_to_asm_schema(test_file: Path) -> None:
    allotrope_dict = from_file(str(test_file.absolute()), VENDOR_TYPE)
    validate_schema(
        allotrope_dict, "light-obscuration/REC/2021/12/light-obscuration.json"
    )


@pytest.mark.short
def test_parse_beckman_hiac_to_asm_contents(test_file: Path) -> None:
    expected_filepath = str(test_file.absolute()).replace(".xlsx", ".json")
    allotrope_dict = from_file(str(test_file.absolute()), VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
