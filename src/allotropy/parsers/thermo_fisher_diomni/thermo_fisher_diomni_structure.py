"""Data structures for Thermo Fisher Diomni parser."""

from __future__ import annotations

from pathlib import PureWindowsPath
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    ContainerType,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    SampleRoleType,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_or_none,
)


def create_metadata(header: SeriesData, file_path: str | None) -> Metadata:
    """Create Metadata object from header data."""
    # Extract software info
    software_name = header.get(str, "Software name", "Diomni")
    software_version = header.get(str, "Software version", NOT_APPLICABLE)

    # Extract instrument info
    instrument_name = header.get(str, "Instrument Name", NOT_APPLICABLE)
    instrument_type = header.get(str, "Instrument Type", NOT_APPLICABLE)
    instrument_serial = header.get(str, "Instrument Serial Number", NOT_APPLICABLE)

    # Extract file name
    file_name_raw = header.get(str, "File Name", "")
    experimental_data_id = (
        PureWindowsPath(file_name_raw).name if file_name_raw else NOT_APPLICABLE
    )

    return Metadata(
        asm_file_identifier=random_uuid_str(),
        file_name=experimental_data_id,
        unc_path=file_path or NOT_APPLICABLE,
        device_identifier=instrument_name,
        model_number=instrument_type,
        device_serial_number=instrument_serial,
        measurement_method_identifier=header.get(
            str, "Quantification Cycle Method", NOT_APPLICABLE
        ),
        software_name=software_name,
        software_version=software_version,
        data_system_instance_identifier=NOT_APPLICABLE,
        device_type="qPCR",
        experiment_type="qPCR experiment",
        container_type=ContainerType.well_plate,
    )


def create_measurement_groups(
    header: SeriesData, measurements_data: pd.DataFrame
) -> list[MeasurementGroup]:
    """Create MeasurementGroup objects from measurement data.

    Creates one MeasurementGroup per well location identifier, following the
    same structure as Design & Analysis adapter.
    """
    # Get block type to determine plate well count
    block_type = header.get(str, "Block Type", "")
    plate_well_count = 384 if "384" in block_type else 96

    # Extract file name for experimental data identifier
    file_name_raw = header.get(str, "File Name", "")
    experimental_data_id = (
        PureWindowsPath(file_name_raw).name if file_name_raw else NOT_APPLICABLE
    )

    # Get well volume from block type or sample volume
    well_volume = _get_well_volume(header, block_type)

    # Get measurement timestamp
    measurement_time = header.get(str, "Run End Data/Time") or header.get(
        str, "Run End Date/Time", NOT_APPLICABLE
    )

    # Group measurements by well location
    measurement_groups = []
    for _, well_data in measurements_data.groupby("Well"):
        measurements = []
        for _, row in well_data.iterrows():
            # Extract sample identifier
            sample_id: Any = row.get("Sample")
            if pd.isna(sample_id):
                sample_id = row.get("Well")

            # Extract target
            target: Any = row.get("Target", NOT_APPLICABLE)

            # Determine sample role type from "Sample type" column
            sample_type_raw: Any = row.get("Sample type")
            sample_type: str | None = (
                str(sample_type_raw)
                if sample_type_raw is not None and not pd.isna(sample_type_raw)
                else None
            )
            sample_role_type = _get_sample_role_type(sample_type)

            # Extract Cq value and other results
            cq_raw: Any = row.get("Cq")
            cq_value = try_float_or_none(cq_raw if not pd.isna(cq_raw) else None)
            reporter: Any = row.get("Reporter")
            delta_rn_raw: Any = row.get("Delta Rn")
            delta_rn = try_float_or_none(
                delta_rn_raw if not pd.isna(delta_rn_raw) else None
            )

            # Build custom info from additional columns
            custom_info: dict[str, Any] = {}
            call_raw: Any = row.get("Call")
            if call_raw and not pd.isna(call_raw):
                custom_info["call"] = str(call_raw)
            cq_conf_raw: Any = row.get("Cq confidence")
            cq_conf = try_float_or_none(
                cq_conf_raw if not pd.isna(cq_conf_raw) else None
            )
            if cq_conf:  # Preserve original behavior: treats 0.0 as falsy
                custom_info["cq_confidence"] = cq_conf
            amp_score_raw: Any = row.get("Amp score")
            amp_score = try_float_or_none(
                amp_score_raw if not pd.isna(amp_score_raw) else None
            )
            if amp_score:  # Preserve original behavior: treats 0.0 as falsy
                custom_info["amp_score"] = amp_score
            amp_status_raw: Any = row.get("Amp status")
            if amp_status_raw and not pd.isna(amp_status_raw):
                custom_info["amp_status"] = str(amp_status_raw)
            quality_issues_raw: Any = row.get("Quality issue(s)")
            if quality_issues_raw and not pd.isna(quality_issues_raw):
                custom_info["quality_issues"] = str(quality_issues_raw)

            # Create processed data
            processed_data = ProcessedData(
                cycle_threshold_result=cq_value,
                baseline_corrected_reporter_result=delta_rn,
                custom_info=custom_info if custom_info else None,
            )

            measurement = Measurement(
                identifier=random_uuid_str(),
                timestamp=measurement_time,
                sample_identifier=str(sample_id) if sample_id else NOT_APPLICABLE,
                target_identifier=str(target),
                location_identifier=str(row.get("Well", NOT_APPLICABLE)),
                well_location_identifier=str(row.get("Well")),
                reporter_dye_setting=str(reporter) if reporter else None,
                sample_role_type=sample_role_type,
                processed_data=processed_data,
            )
            measurements.append(measurement)

        # Create one MeasurementGroup per well location
        measurement_groups.append(
            MeasurementGroup(
                measurements=measurements,
                plate_well_count=plate_well_count,
                experimental_data_identifier=experimental_data_id,
                well_volume=well_volume,
                analyst=header.get(str, "Operator"),
            )
        )

    return measurement_groups


def _get_well_volume(header: SeriesData, block_type: str) -> float:
    """Get well volume from header or block type."""
    # Try to get from Sample Volume field first
    sample_volume = header.get(float, "Sample Volume")
    if sample_volume is not None:
        return sample_volume

    # Otherwise infer from block type (same logic as QuantStudio parser)
    if well_search := re.search(r"([0-9]+\.[0-9]+)-?mL", block_type):
        return float(well_search.groups()[0]) * 1000
    elif "384-Well Block" in block_type:
        return 40.0
    elif "Taqman Array Card" in block_type:
        return 1.5

    # Default fallback
    return 15.0


def _get_sample_role_type(sample_type: str | None) -> SampleRoleType | None:
    """Map sample type to SampleRoleType."""
    if not sample_type:
        return None

    sample_type_upper = str(sample_type).upper()

    if "UNKNOWN" in sample_type_upper:
        return SampleRoleType.unknown_sample_role
    elif "NTC" in sample_type_upper or "NEGATIVE" in sample_type_upper:
        return SampleRoleType.control_sample_role
    elif "STANDARD" in sample_type_upper:
        return SampleRoleType.standard_sample_role
    elif "CONTROL" in sample_type_upper or "POSITIVE" in sample_type_upper:
        return SampleRoleType.control_sample_role

    return None
