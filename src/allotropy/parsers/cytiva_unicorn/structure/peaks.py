from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from allotropy.allotrope.models.shared.definitions.definitions import (
    TQuantityValue,
)
from allotropy.allotrope.models.shared.definitions.quantity_values import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliliter,
    TQuantityValuePercent,
    TQuantityValueSiemensPerMeter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Peak,
)
from allotropy.parsers.cytiva_unicorn.constants import (
    PEAK_AREA_UNIT,
    PEAK_END_UNIT,
    PEAK_START_UNIT,
    PEAK_WIDTH_AT_HALF_HEIGHT_UNIT,
    PEAK_WIDTH_UNIT,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none

# Peak tables keyed by the CurveNumber of the curve they were evaluated on.
PeakTables = dict[str, list[StrictXmlElement]]


@dataclass(frozen=True)
class PeakUnits:
    height_unit: str
    area_unit: str
    height_quantity: type[TQuantityValue]
    # Divisors converting Unicorn's height/area values to height_unit/area_unit.
    height_divisor: int
    area_divisor: int

    def height(self, value: float | None) -> float | None:
        return _divide(value, self.height_divisor)

    def area(self, value: float | None) -> float | None:
        return _divide(value, self.area_divisor)


def _divide(value: float | None, divisor: int) -> float | None:
    # Divide in decimal to avoid float noise in converted values (e.g. 7.203249 / 10000).
    return None if value is None else float(Decimal(str(value)) / divisor)


# Keyed by the Unicorn height unit of the evaluated curve. Conductivity is converted from
# mS/cm to S/m (and ml*mS/cm to [S/m].L) to match the conductivity data cube.
PEAK_UNITS = {
    "mAU": PeakUnits("mAU", PEAK_AREA_UNIT, TQuantityValueMilliAbsorbanceUnit, 1, 1),
    "mS/cm": PeakUnits("S/m", "[S/m].L", TQuantityValueSiemensPerMeter, 10, 10 * 1000),
}


def get_peak_tables(chromatogram: StrictXmlElement) -> PeakTables:
    peak_tables: PeakTables = defaultdict(list)
    if tables := chromatogram.find_or_none("PeakTables"):
        for table in tables.findall("PeakTable"):
            curve_number = table.recursive_find_or_none(["DataCurve", "CurveNumber"])
            if curve_number and (number := curve_number.get_text_or_none()):
                peak_tables[number].append(table)
    return dict(peak_tables)


def _get_conductivity(peak: StrictXmlElement, name: str) -> TQuantityValue | None:
    value = peak.get_sub_float_or_none(name)
    return TQuantityValueSiemensPerMeter(value=value / 10) if value else None


def _get_peak_custom_info(
    peak: StrictXmlElement, units: PeakUnits | None
) -> dict[str, TQuantityValue | None]:
    endpoint_heights = (
        {
            "start peak end point height": quantity_or_none(
                units.height_quantity,
                units.height(peak.get_sub_float_or_none("StartPeakEndpointHeight")),
            ),
            "end peak end point height": quantity_or_none(
                units.height_quantity,
                units.height(peak.get_sub_float_or_none("EndPeakEndpointHeight")),
            ),
        }
        if units
        else {}
    )
    return {
        "max peak retention": quantity_or_none(
            TQuantityValueMilliliter,
            peak.get_sub_float_or_none("MaxPeakRetention"),
        ),
        "percent of total area": quantity_or_none(
            TQuantityValuePercent,
            peak.get_sub_float_or_none("PercentOfTotalArea"),
        ),
        **endpoint_heights,
        "sigma": quantity_or_none(
            TQuantityValueUnitless,
            peak.get_sub_float_or_none("Sigma"),
        ),
        "asymmetry peak start": quantity_or_none(
            TQuantityValueUnitless,
            peak.get_sub_float_or_none("AssymetryPeakStart"),
        ),
        "asymmetry peak end": quantity_or_none(
            TQuantityValueUnitless,
            peak.get_sub_float_or_none("AssymetryPeakEnd"),
        ),
        "start conductivity height": _get_conductivity(peak, "StartConductivityHeight"),
        "max conductivity height": _get_conductivity(peak, "MaxConductivityHeight"),
        "end conductivity height": _get_conductivity(peak, "EndConductivityHeight"),
        "average conductivity": _get_conductivity(peak, "AverageConductivity"),
    }


def _create_peak(peak: StrictXmlElement, index: int, units: PeakUnits | None) -> Peak:
    # If the curve unit is not supported, height and area are left unread and reported
    # as raw values in custom info.
    peak_obj = Peak(
        identifier=random_uuid_str(),
        index=f"Peak {index}",
        end=peak.get_sub_float_or_none("EndPeakRetention"),
        end_unit=PEAK_END_UNIT,
        height=units.height(peak.get_sub_float_or_none("Height")) if units else None,
        height_unit=units.height_unit if units else None,
        written_name=peak.get_sub_text_or_none("Name"),
        area=units.area(peak.get_sub_float_or_none("Area")) if units else None,
        area_unit=units.area_unit if units else None,
        relative_area=peak.get_sub_float_or_none("PercentOfTotalPeakArea"),
        start=peak.get_sub_float_or_none("StartPeakRetention"),
        start_unit=PEAK_START_UNIT,
        chromatographic_resolution=peak.get_sub_float_or_none("Resolution"),
        width_at_half_height=peak.get_sub_float_or_none("WidthAtHalfHeight"),
        width_at_half_height_unit=PEAK_WIDTH_AT_HALF_HEIGHT_UNIT,
        width=peak.get_sub_float_or_none("Width"),
        width_unit=PEAK_WIDTH_UNIT,
        chromatographic_asymmetry=peak.get_sub_float_or_none("Assymetry"),
        custom_info=_get_peak_custom_info(peak, units),
    )
    if peak_obj.custom_info is not None:
        peak_obj.custom_info.update(peak.get_unread())
    return peak_obj


def create_peaks(peak_tables: PeakTables, curve: StrictXmlElement) -> list[Peak]:
    curve_number = curve.get_sub_text_or_none("CurveNumber")
    curve_unit = curve.get_sub_text_or_none("AmplitudeUnit")
    output: list[Peak] = []
    for table in peak_tables.get(curve_number or "", []):
        table_unit = table.recursive_find_or_none(["PeakUnit", "HeightUnit"])
        unit = (table_unit.get_text_or_none() if table_unit else None) or curve_unit
        units = PEAK_UNITS.get(unit or "")
        peaks = table.find_or_none("Peaks")
        for peak in peaks.findall("Peak") if peaks else []:
            output.append(_create_peak(peak, len(output) + 1, units))
    return output
