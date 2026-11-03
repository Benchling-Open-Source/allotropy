"""Tests for OpenLab CDS total peak area edge cases that the test data files do not cover."""
from typing import Any

import pytest

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


def _total_peak_area(*peaks: dict[str, Any]) -> dict[str, Any] | None:
    return get_total_peak_area(list(peaks), create_peak(list(peaks)))


def test_total_peak_area_sums_areas() -> None:
    assert _total_peak_area(
        _peak(Area={"@val": "100.5", "@unit": "mAU·s"}),
        _peak(Area={"@val": "200.25", "@unit": "mAU·s"}),
    ) == {"total peak area": {"value": 300.75, "unit": "mAU.s"}}


def test_total_peak_area_without_peaks_is_not_reported() -> None:
    assert _total_peak_area() is None


@pytest.mark.parametrize(
    "area",
    [
        pytest.param({}, id="empty"),
        pytest.param({"@val": "", "@unit": "mAU·s"}, id="unparseable"),
        pytest.param({"@val": "200.0"}, id="no unit"),
    ],
)
def test_total_peak_area_with_a_peak_lacking_an_area_is_not_reported(
    area: dict[str, str],
) -> None:
    assert _total_peak_area(_peak(), _peak(Area=area)) is None


def test_total_peak_area_of_mixed_units_is_not_reported() -> None:
    assert (
        _total_peak_area(
            _peak(Area={"@val": "100.0", "@unit": "mAU·s"}),
            _peak(Area={"@val": "200.0", "@unit": "mAU·min"}),
        )
        is None
    )
