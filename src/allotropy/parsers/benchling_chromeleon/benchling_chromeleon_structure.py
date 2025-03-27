from pathlib import Path
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import (
    Microliter,
    MilliAbsorbanceUnit,
    MilliAbsorbanceUnitTimesSecond,
    Milliliter,
    SecondTime,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    DeviceDocument,
    Measurement,
    MeasurementGroup,
    Metadata,
    Peak,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.benchling_chromeleon import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float, try_float_or_none


def _create_device_documents(
    device_information: dict[str, Any]
) -> list[DeviceDocument] | None:
    return [
        DeviceDocument(
            device_type="pump",
            model_number=device_information.get("pump model number") or NOT_APPLICABLE,
        ),
        DeviceDocument(
            device_type="uv",
            model_number=device_information.get("uv model number") or NOT_APPLICABLE,
        ),
        DeviceDocument(
            device_type="sampler",
            model_number=device_information.get("sampler model number")
            or NOT_APPLICABLE,
        ),
    ]


def create_metadata(
    first_injection: dict[str, Any],
    sequence: dict[str, Any],
    file_path: str,
    device_information: dict[str, Any],
) -> Metadata:
    return Metadata(
        asset_management_identifier=first_injection.get(
            "precondition system instrument name", NOT_APPLICABLE
        ),
        software_name=constants.SOFTWARE_NAME,
        file_name=Path(file_path).name,
        unc_path=file_path,
        description=first_injection.get("description"),
        device_documents=_create_device_documents(device_information),
        lc_agg_custom_info={
            "Sequence Creation Time": sequence.get("sequence creation time"),
            "Sequence Directory": sequence.get("sequence directory"),
            "Sequence Name": sequence.get("sequence name"),
            "Sequence Update operator": sequence.get("sequence update operator"),
            "Sequence Update Time": sequence.get("sequence update time"),
            "Number of Injections": sequence.get("number of injections"),
        },
    )


def _validate_injection_volume_unit(injection_volume: float, unit: str) -> float:
    # if unit is Milliliter, convert to Microliter
    if unit == Milliliter.unit:
        return injection_volume * 1000
    if unit != Microliter.unit:
        msg = f"Invalid injection volume unit: {unit}"
        raise AllotropeConversionError(msg)
    return injection_volume


def _get_chromatogram(signal: dict[str, Any]) -> DataCube | None:
    chrom: dict[str, list[float]] | None = signal.get("chromatogram")
    if not chrom:
        return None
    if len(chrom) != 2:
        msg = "Expected chrom to have two lists"
        raise AllotropeConversionError(msg)

    dimensions = chrom["x"]
    measures = chrom["y"]

    # ASM expected chromatogram dimensions (x axis) to be in seconds, but Chromeleon reports it in minutes,
    # so convert here.
    dimensions = [t * 60 for t in dimensions]

    return DataCube(
        label=signal["signal name"],
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="retention time",
                unit=SecondTime.unit,
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="absorbance",
                unit=MilliAbsorbanceUnit.unit,
            )
        ],
        dimensions=[dimensions],
        measures=[measures],
    )


def _convert_to_seconds(value: float | None) -> float | None:
    # Assume value is in minutes
    return value * 60 if value is not None else None


def _create_peak(peak: dict[str, Any], signal: dict[str, Any]) -> Peak:
    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Chromeleon software, 1V == 1AU, so we just need to convert μ to m
    if (area := try_float_or_none(peak.get("area"))) is not None:
        area /= 1000
    if (height := try_float_or_none(peak.get("height"))) is not None:
        height /= 1000
    # Times are reported in minutes by Chromeleon - convert to seconds
    retention_time = _convert_to_seconds(try_float_or_none(peak.get("retention time")))
    width_at_half_height = _convert_to_seconds(
        try_float_or_none(peak.get("peak width at half height"))
    )
    peak_width_at_5_percent_of_height = _convert_to_seconds(
        try_float_or_none(peak.get("peak width at 5 % of height"))
    )
    peak_width_at_10_percent_of_height = _convert_to_seconds(
        try_float_or_none(peak.get("peak width at 10 % of height"))
    )
    peak_width_at_baseline = _convert_to_seconds(
        try_float_or_none(peak.get("peak width at baseline"))
    )
    baseline_value_at_start_of_peak = _convert_to_seconds(
        try_float_or_none(peak.get("start value baseline"))
    )
    baseline_value_at_end_of_peak = _convert_to_seconds(
        try_float_or_none(peak.get("stop value baseline"))
    )
    peak_right_width_at_10_percent_height = _convert_to_seconds(
        try_float_or_none(peak.get("peak right width at 10 % of height"))
    )
    peak_left_width_at_10_percent_height = _convert_to_seconds(
        try_float_or_none(peak.get("peak left width at 10 % of height"))
    )
    peak_group = _convert_to_seconds(try_float_or_none(peak.get("group area")))

    return Peak(
        identifier=random_uuid_str(),
        index=peak.get("identifier"),
        start=try_float(peak.get("start time"), "start time") * 60,
        start_unit=SecondTime.unit,
        end=try_float(peak.get("end time"), "end time") * 60,
        end_unit=SecondTime.unit,
        retention_time=retention_time,
        area=area,
        area_unit=MilliAbsorbanceUnitTimesSecond.unit,
        relative_area=try_float_or_none(peak.get("relative peak area")),
        width=try_float_or_none(peak.get("Width")),
        height=height,
        height_unit="mAU",
        relative_height=try_float_or_none(peak.get("relative peak height")),
        written_name=peak.get("name"),
        relative_retention_time=try_float_or_none(peak.get("relative retention time")),
        capacity_factor=try_float_or_none(peak.get("capacity factor")),
        chromatographic_resolution=try_float_or_none(
            peak.get("chromatographic peak resolution")
        ),
        number_of_theoretical_plates_by_peak_width_at_half_height=try_float_or_none(
            peak.get("number of theoretical plates by peak width at half height")
        ),
        width_at_half_height=width_at_half_height,
        peak_width_at_5_percent_of_height=peak_width_at_5_percent_of_height,
        peak_width_at_10_percent_of_height=peak_width_at_10_percent_of_height,
        peak_width_at_baseline=peak_width_at_baseline,
        asymmetry_factor_measured_at_5_percent_height=try_float_or_none(
            peak.get("asymmetry factor measured at 5 % height")
        ),
        peak_analyte_amount=try_float_or_none(peak.get("amount")),
        relative_corrected_peak_area=try_float_or_none(peak.get("rel ce area total")),
        peak_group=peak_group,
        baseline_value_at_start_of_peak=baseline_value_at_start_of_peak,
        baseline_value_at_end_of_peak=baseline_value_at_end_of_peak,
        custom_info={
            "number of peaks": signal.get("number of peaks"),
            "peak right width at 10% height": peak_right_width_at_10_percent_height,
            "peak left width at 10% height": peak_left_width_at_10_percent_height,
            "chromatographic peak resolution (usp)": peak.get(
                "chromatographic peak resolution (USP)"
            ),
            "asymmetry aia": peak.get("asymmetry aia"),
        },
    )


def _create_measurements(injection: dict[str, Any]) -> list[Measurement] | None:
    injection_volume_setting = injection.get("injection volume setting")
    injection_volume_unit = injection.get("injection volume unit")
    if injection_volume_setting and injection_volume_unit:
        injection_volume_setting = _validate_injection_volume_unit(
            injection_volume_setting, injection_volume_unit
        )

    signals = injection.get("signals", [])
    if len(signals) == 0:
        return None
    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            description=injection.get("description"),
            sample_identifier=injection["sample identifier"],
            location_identifier=injection.get("location identifier"),
            well_location_identifier=injection.get("custom variables", {}).get("Well"),
            observation=injection.get("custom variables", {}).get("Observation"),
            sample_custom_info={
                "sample precipitation": injection.get("custom variables", {}).get(
                    "Sample_Precipitation"
                ),
                "rack type": injection.get("custom variables", {}).get("Rack_Type"),
                "stability": injection.get("custom variables", {}).get("Stability"),
                "req id": injection.get("custom variables", {}).get("REQ_ID"),
                "additional comment": injection.get("custom variables", {}).get(
                    "Additional_Comment"
                ),
            },
            device_control_docs=[
                DeviceControlDoc(
                    device_type=constants.DEVICE_TYPE,
                    detection_type=signal.get("detection type"),
                    detector_offset_setting=val
                    if (val := signal.get("detector offset setting")) != "unknown"
                    else None,
                    detector_wavelength_setting=signal.get("wavelength setting"),
                    detector_sampling_rate_setting=val
                    if (val := signal.get("detector sampling rate setting"))
                    != "unknown"
                    else None,
                    detector_bandwidth_setting=signal.get("bandwidth setting"),
                    electronic_absorbance_reference_wavelength_setting=signal.get(
                        "reference wavelength setting"
                    ),
                    electronic_absorbance_reference_bandwidth_setting=signal.get(
                        "reference bandwidth setting"
                    ),
                )
            ],
            injection_identifier=injection["injection identifier"],
            injection_time=injection["injection time"],
            injection_volume_setting=injection_volume_setting,
            injection_custom_info={
                "injection": injection.get("injection number"),
                "injection name": injection.get("injection name"),
                "injection position": injection.get("injection position"),
                "injection status": injection.get("injection status"),
                "injection type": injection.get("injection type"),
                "last update user name": injection.get("last update user name"),
                "creation user name": injection.get("creation user name"),
                "injection program": injection.get("injection program"),
                "injection method": injection.get("injection method"),
            },
            chromatography_serial_num=NOT_APPLICABLE,
            chromatogram_data_cube=_get_chromatogram(signal) if signal else None,
            peaks=[_create_peak(peak, signal) for peak in signal.get("peaks", [])],
        )
        for signal in injection.get("signals", [])
    ]


def create_measurement_groups(
    injections: list[dict[str, Any]]
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(measurements=measurements)
        for sample_injections in injections
        if (measurements := _create_measurements(sample_injections)) is not None
    ]
