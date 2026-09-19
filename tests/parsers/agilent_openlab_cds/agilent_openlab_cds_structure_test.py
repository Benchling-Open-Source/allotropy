"""Tests for OpenLab CDS peak results that the test data files do not cover.

Molar mass results are only reported for size-exclusion methods with a GPC calibration, and no
result set we have was acquired with one, so they are covered here from peak data directly.
"""
from typing import Any

import pytest

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Peak,
)
from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_structure import (
    create_peak,
    get_total_peak_area,
)


def _peak(**elements: Any) -> dict[str, Any]:
    return {
        "@id": "peak-1",
        "RetentionTime": {"@val": "2.5", "@unit": "min"},
        "Area": {"@val": "2761.5", "@unit": "mAU·s"},
        "AreaPercent": {"@val": "27.7"},
        "Height": {"@val": "123.2", "@unit": "mAU"},
        "BeginTime": {"@val": "2.35", "@unit": "min"},
        "EndTime": {"@val": "2.81", "@unit": "min"},
        **elements,
    }


def test_peak_reports_molar_mass_results() -> None:
    (peak,) = create_peak(
        [
            _peak(
                Mn={"@val": "148532.0"},
                Mw={"@val": "151203.5"},
                PD={"@val": "1.018"},
            )
        ]
    )
    assert peak.custom_info == {
        "Mn": {"value": 148532.0, "unit": "g/mol"},
        "Mw": {"value": 151203.5, "unit": "g/mol"},
        "polydispersity": {"value": 1.018, "unit": "(unitless)"},
    }


def test_peak_without_molar_mass_results_reports_none() -> None:
    (peak,) = create_peak([_peak()])
    assert peak.custom_info == {}


def test_total_peak_area_sums_areas() -> None:
    peaks = create_peak(
        [
            _peak(Area={"@val": "100.5", "@unit": "mAU·s"}),
            _peak(Area={"@val": "200.25", "@unit": "mAU·s"}),
        ]
    )
    assert get_total_peak_area(peaks) == {
        "total peak area": {"value": 300.75, "unit": "mAU.s"}
    }


@pytest.mark.parametrize("peaks", [None, [], [Peak(identifier="peak-1")]])
def test_total_peak_area_without_areas_is_not_reported(
    peaks: list[Peak] | None,
) -> None:
    assert get_total_peak_area(peaks) is None


def test_total_peak_area_of_mixed_units_is_not_reported() -> None:
    peaks = [
        Peak(identifier="peak-1", area=100.0, area_unit="mAU.s"),
        Peak(identifier="peak-2", area=200.0, area_unit="RFU.s"),
    ]
    assert get_total_peak_area(peaks) is None
