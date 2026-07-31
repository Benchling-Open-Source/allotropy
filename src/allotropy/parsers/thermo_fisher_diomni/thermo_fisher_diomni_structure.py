"""Data structures for Thermo Fisher Diomni parser."""

from __future__ import annotations

from pathlib import PureWindowsPath
import re

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
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none, try_int


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
    experimental_data_id = PureWindowsPath(file_name_raw).name if file_name_raw else NOT_APPLICABLE

    return Metadata(
        asm_file_identifier=random_uuid_str(),
        file_name=experimental_data_id,
        unc_path=file_path or NOT_APPLICABLE,
        device_identifier=instrument_name,
        model_number=instrument_type,
        device_serial_number=instrument_serial,
        measurement_method_identifier=header.get(str, "Quantification Cycle Method", NOT_APPLICABLE),
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
    """Create MeasurementGroup objects from measurement data."""
    # Get block type to determine plate well count
    block_type = header.get(str, "Block Type", "")
    plate_well_count = 384 if "384" in block_type else 96

    # Extract file name for experimental data identifier
    file_name_raw = header.get(str, "File Name", "")
    experimental_data_id = PureWindowsPath(file_name_raw).name if file_name_raw else NOT_APPLICABLE

    # Get well volume from block type or sample volume
    well_volume = _get_well_volume(header, block_type)

    # Get measurement timestamp
    measurement_time = header.get(str, "Run End Data/Time") or header.get(str, "Run End Date/Time", NOT_APPLICABLE)

    measurements = []
    for _, row in measurements_data.iterrows():
        # Extract sample identifier
        sample_id = row.get("Sample")
        if pd.isna(sample_id):
            sample_id = row.get("Well")

        # Extract target
        target = row.get("Target", NOT_APPLICABLE)

        # Determine sample role type from "Sample type" column
        sample_type = row.get("Sample type")
        sample_role_type = _get_sample_role_type(sample_type)

        # Extract Cq value and other results
        cq_value = try_float_or_none(row.get("Cq"))
        reporter = row.get("Reporter")
        delta_rn = try_float_or_none(row.get("Delta Rn"))

        # Build custom info from additional columns
        custom_info = {}
        if call := row.get("Call"):
            custom_info["call"] = call
        if cq_conf := try_float_or_none(row.get("Cq confidence")):
            custom_info["cq_confidence"] = cq_conf
        if amp_score := try_float_or_none(row.get("Amp score")):
            custom_info["amp_score"] = amp_score
        if amp_status := row.get("Amp status"):
            custom_info["amp_status"] = amp_status
        if quality_issues := row.get("Quality issue(s)"):
            custom_info["quality_issues"] = quality_issues

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

    # Group all measurements together
    return [
        MeasurementGroup(
            measurements=measurements,
            plate_well_count=plate_well_count,
            experimental_data_identifier=experimental_data_id,
            well_volume=well_volume,
            analyst=header.get(str, "Operator"),
        )
    ]


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
