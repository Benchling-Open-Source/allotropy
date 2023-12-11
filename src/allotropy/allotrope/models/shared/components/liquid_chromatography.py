from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValuePercent,
    TQuantityValueSecondTime,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TQuantityValue,
    TStringValue,
)
from allotropy.exceptions import AllotropeConversionError


@dataclass
class PeakItem:
    retention_time: TQuantityValueSecondTime
    peak_end: Optional[TQuantityValueSecondTime] = None
    identifier: Optional[TStringValue] = None
    relative_peak_height: Optional[TQuantityValuePercent] = None
    written_name: Optional[TStringValue] = None
    peak_height: Optional[TQuantityValue] = None
    capacity_factor__chromatography_: Optional[TQuantityValueUnitless] = None
    peak_area: Optional[TQuantityValue] = None
    relative_peak_area: Optional[TQuantityValuePercent] = None
    peak_start: Optional[TQuantityValueSecondTime] = None
    peak_selectivity__chromatography_: Optional[TQuantityValueUnitless] = None

    peak_width_at_4_4___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_13_4___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_32_4___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_60_7___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_half_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_5___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width_at_baseline: Optional[TQuantityValueSecondTime] = None
    peak_width_at_inflection: Optional[TQuantityValueSecondTime] = None
    peak_width_at_10___of_height: Optional[TQuantityValueSecondTime] = None
    peak_width: Optional[TQuantityValueSecondTime] = None
    statistical_skew__chromatography_: Optional[TQuantityValueUnitless] = None
    asymmetry_factor_measured_at_5___height: Optional[TQuantityValueUnitless] = None
    asymmetry_factor_measured_at_10___height: Optional[TQuantityValueUnitless] = None
    asymmetry_factor_squared_measured_at_10___height: Optional[
        TQuantityValueUnitless
    ] = None
    asymmetry_factor_squared_measured_at_4_4___height: Optional[
        TQuantityValueUnitless
    ] = None
    asymmetry_factor_measured_at_4_4___height: Optional[TQuantityValueUnitless] = None
    chromatographic_peak_asymmetry_factor: Optional[TQuantityValueUnitless] = None
    asymmetry_factor_measured_at_baseline: Optional[TQuantityValueUnitless] = None
    chromatographic_peak_resolution: Optional[TQuantityValueUnitless] = None
    chromatographic_peak_resolution_using_baseline_peak_widths: Optional[
        TQuantityValueUnitless
    ] = None
    chromatographic_peak_resolution_using_peak_width_at_half_height: Optional[
        TQuantityValueUnitless
    ] = None
    chromatographic_peak_resolution_using_statistical_moments: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates__chromatography_: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_measured_at_60_7___of_peak_height: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_measured_at_32_4___of_peak_height: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_measured_at_13_4___of_peak_height: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_measured_at_4_4___of_peak_height: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_by_tangent_method: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_by_peak_width_at_half_height: Optional[
        TQuantityValueUnitless
    ] = None
    number_of_theoretical_plates_by_peak_width_at_half_height__JP14_: Optional[
        TQuantityValueUnitless
    ] = None

    def __post_init__(self) -> None:
        any_of_keys = [
            "peak_width_at_4_4___of_height",
            "peak_width_at_13_4___of_height",
            "peak_width_at_32_4___of_height",
            "peak_width_at_60_7___of_height",
            "peak_width_at_half_height",
            "peak_width_at_5___of_height",
            "peak_width_at_baseline",
            "peak_width_at_inflection",
            "peak_width_at_10___of_height",
            "peak_width",
            "statistical_skew__chromatography_",
            "asymmetry_factor_measured_at_5___height",
            "asymmetry_factor_measured_at_10___height",
            "asymmetry_factor_squared_measured_at_10___height",
            "asymmetry_factor_squared_measured_at_4_4___height",
            "asymmetry_factor_measured_at_4_4___height",
            "chromatographic_peak_asymmetry_factor",
            "asymmetry_factor_measured_at_baseline",
            "chromatographic_peak_resolution",
            "chromatographic_peak_resolution_using_baseline_peak_widths",
            "chromatographic_peak_resolution_using_peak_width_at_half_height",
            "chromatographic_peak_resolution_using_statistical_moments",
            "number_of_theoretical_plates__chromatography_",
            "number_of_theoretical_plates_measured_at_60_7___of_peak_height",
            "number_of_theoretical_plates_measured_at_32_4___of_peak_height",
            "number_of_theoretical_plates_measured_at_13_4___of_peak_height",
            "number_of_theoretical_plates_measured_at_4_4___of_peak_height",
            "number_of_theoretical_plates_by_tangent_method",
            "number_of_theoretical_plates_by_peak_width_at_half_height",
            "number_of_theoretical_plates_by_peak_width_at_half_height__JP14_",
        ]
        # Logic for enforcing anyOf
        if all(getattr(self, key) is None for key in any_of_keys):
            error = f"At least one of {any_of_keys} must be set on a peak."
            raise AllotropeConversionError(error)


@dataclass
class PeakList:
    peak: Optional[list[PeakItem]] = None
