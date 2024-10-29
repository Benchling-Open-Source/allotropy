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
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import Header
from allotropy.testing.utils import get_testdata_dir

TESTDATA = get_testdata_dir(__file__)


def test_get_model() -> None:
    model = PharmSpecParser().to_allotrope(
        NamedFileContents(open(Path(TESTDATA, "hiac_example_1.xlsx"), "rb"), "")
    )
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


@pytest.mark.parametrize(
    "title,version",
    [
        ["HIAC PharmSpec v3.0 Summary Report", "3.0"],
        ["HIAC PharmSpec v3.0.1 Summary Report", "3.0.1"],
        ["HIAC PharmSpec v3 Summary Report", "3"],
        ["HIAC PharmSpec v Summary Report", "Unknown"],
        ["HIAC PharmSpec v3.0.10 Summary Report", "3.0.10"],
        ["HIAC PharmSpec v3.0.10.40 Summary Report", "3.0.10"],
    ],
)
def test_get_software_version_report_string(title: str, version: str) -> None:
    assert Header._get_software_version_report_string(title) == version
