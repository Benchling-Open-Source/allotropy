from pathlib import Path

import pytest

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    DeviceSystemDocument,
    DistributionAggregateDocument,
    DistributionDocumentItem,
    MeasurementDocument,
    ProcessedDataAggregateDocument,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import Header
from allotropy.testing.utils import get_testdata_dir

TESTDATA = get_testdata_dir(__file__)


def test_get_model() -> None:
    model = PharmSpecParser().to_allotrope(
        NamedFileContents(
            open(Path(TESTDATA, "hiac_example_1.xlsx"), "rb"), "hiac_example_1.xlsx"
        )
    )
    assert isinstance(
        model.solution_analyzer_aggregate_document, SolutionAnalyzerAggregateDocument
    )
    assert isinstance(
        model.solution_analyzer_aggregate_document.device_system_document,
        DeviceSystemDocument,
    )
    assert (
        model.solution_analyzer_aggregate_document.device_system_document.equipment_serial_number
        == "1808303021"
    )

    assert (
        model.solution_analyzer_aggregate_document.solution_analyzer_document[
            0
        ].measurement_aggregate_document.measurement_document
        is not None
    )

    assert isinstance(
        model.solution_analyzer_aggregate_document.solution_analyzer_document[
            0
        ].measurement_aggregate_document.measurement_document[0],
        MeasurementDocument,
    )

    assert isinstance(
        model.solution_analyzer_aggregate_document.solution_analyzer_document[0]
        .measurement_aggregate_document.measurement_document[0]
        .sample_document,
        SampleDocument,
    )

    assert (
        model.solution_analyzer_aggregate_document.solution_analyzer_document[0]
        .measurement_aggregate_document.measurement_document[0]
        .sample_document.sample_identifier
        == "ExampleTimepoint"
    )

    assert (
        len(
            model.solution_analyzer_aggregate_document.solution_analyzer_document[
                0
            ].measurement_aggregate_document.measurement_document
        )
        == 2
    )
    for elem in model.solution_analyzer_aggregate_document.solution_analyzer_document[
        0
    ].measurement_aggregate_document.measurement_document:
        assert isinstance(elem, MeasurementDocument)
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
            == 5
        )

        assert isinstance(
            elem.processed_data_aggregate_document.processed_data_document[
                0
            ].distribution_aggregate_document.distribution_document[0],
            DistributionDocumentItem,
        )

        # 5 rows in the distribution document
        assert (
            len(
                elem.processed_data_aggregate_document.processed_data_document[
                    0
                ].distribution_aggregate_document.distribution_document
            )
            == 5
        )

        # Ensure correct order and particle sizes
        for i, particle_size in enumerate([2, 5, 10, 25, 50]):
            test = (
                elem.processed_data_aggregate_document.processed_data_document[0]
                .distribution_aggregate_document.distribution_document[i]
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
