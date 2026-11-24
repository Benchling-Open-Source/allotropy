from pathlib import Path

import pytest

from allotropy.allotrope.models.adm.core.rec._2024._09.hierarchy import (
    DeviceSystemDocument,
)
from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    DistributionAggregateDocument,
    DistributionDocumentItem,
    MeasurementDocumentItem,
    ProcessedDataAggregateDocument,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import (
    create_measurement_groups,
    Distribution,
    Header,
)
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

    meas_agg = model.solution_analyzer_aggregate_document.solution_analyzer_document[
        0
    ].measurement_aggregate_document
    assert meas_agg is not None

    assert meas_agg.measurement_document is not None

    assert isinstance(
        meas_agg.measurement_document[0],
        MeasurementDocumentItem,
    )

    assert isinstance(
        meas_agg.measurement_document[0].sample_document,
        SampleDocument,
    )

    assert (
        meas_agg.measurement_document[0].sample_document.sample_identifier
        == "ExampleTimepoint"
    )

    assert len(meas_agg.measurement_document) == 2
    for elem in meas_agg.measurement_document:
        assert isinstance(elem, MeasurementDocumentItem)
        assert isinstance(elem.measurement_identifier, str)
        assert isinstance(
            elem.processed_data_aggregate_document, ProcessedDataAggregateDocument
        )
        assert len(elem.processed_data_aggregate_document.processed_data_document) == 1
        pdd = elem.processed_data_aggregate_document.processed_data_document[0]
        assert isinstance(
            pdd.distribution_aggregate_document, DistributionAggregateDocument
        )
        dist_docs = pdd.distribution_aggregate_document.distribution_document
        assert dist_docs is not None
        assert len(dist_docs) == 5

        assert isinstance(dist_docs[0], DistributionDocumentItem)

        # Ensure correct order and particle sizes
        for i, particle_size in enumerate([2, 5, 10, 25, 50]):
            test = dist_docs[i].particle_size
            assert test is not None
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


def test_header_custom_info_is_reported_for_every_run() -> None:
    header = Header(
        measurement_time="2022-03-01 10:00:00",
        flush_volume_setting=0,
        detector_view_volume=100.0,
        repetition_setting=3,
        sample_volume_setting=0.2,
        sample_identifier="ExampleTimepoint",
        container_identifier="-",
        dilution_factor_setting=1.0,
        analyst="Operator",
        equipment_serial_number="1808303021",
        software_version="3.0",
        custom_info={
            "Sensor Model": "HRLD150",
            "Batch-Nr": "B-0042",
            "Ro-Nr": "R-7",
            "Bemerkungen 1": "first note",
            "Bemerkungen 2": "-",
        },
    )
    distributions = [
        Distribution(name=name, features=[], is_calculated=False)
        for name in ("Run1", "Run2", "Run3")
    ]

    [group] = create_measurement_groups(header, distributions)

    assert [m.identifier for m in group.measurements] == ["Run1", "Run2", "Run3"]
    for measurement in group.measurements:
        assert measurement.device_control_custom_info == {"model number": "HRLD150"}
        assert measurement.sample_custom_info == {
            "batch identifier": "B-0042",
            "container identifier": None,
        }
        assert measurement.custom_info == {
            "Ro-Nr": "R-7",
            "observation 1": "first note",
            "observation 2": None,
        }
    # Values reported on the measurements are not repeated in the header custom info.
    assert header.custom_info == {"Bemerkungen 2": "-"}
