from pathlib import Path

import pytest

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrometer,
)
from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_hiac.hiac_parser import HIACParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.to_allotrope import allotrope_from_file


@pytest.fixture()
def test_file() -> Path:
    f = Path(__file__).parent / "testdata/hiac_example_1.xlsx"
    return f.absolute()


@pytest.mark.short
def test_get_model(test_file: Path) -> None:
    parser = HIACParser(TimestampParser())
    model = parser._parse(open(test_file, "rb"), "")
    assert model.detector_identifier == "1808303021"
    assert model.sample_identifier == "ExampleTimepoint"
    assert model.measurement_document
    assert model.measurement_document.distribution_document

    # Single distribution document
    assert isinstance(model.measurement_document.distribution_document.items, list)
    assert len(model.measurement_document.distribution_document.items) == 1

    # 5 rows in the distribution document
    assert isinstance(
        model.measurement_document.distribution_document.items[0].items, list
    )
    assert len(model.measurement_document.distribution_document.items[0].items) == 5

    # Ensure correct order and particle sizes
    for i, particle_size in enumerate([2, 5, 10, 25, 50]):
        test = (
            model.measurement_document.distribution_document.items[0]
            .items[i]
            .particle_size
        )
        assert test == TQuantityValueMicrometer(particle_size)


def test_asm(test_file: Path) -> None:
    asm = allotrope_from_file(str(test_file), Vendor.BECKMAN_HIAC)
    assert isinstance(asm, dict)
