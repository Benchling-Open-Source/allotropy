from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueHertz,
    TQuantityValueMilliliter,
    TQuantityValueResponseUnit,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    DeviceControlDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ReportPoint,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_evaluation import constants
from allotropy.parsers.cytiva_biacore_t200_evaluation.constants import (
    DEVICE_IDENTIFIER,
    MODEL_NUMBER,
)
from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_decoder import (
    decode_data,
)
from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_structure import (
    _extract_value_from_xml_element_or_dict,
    CalculatedValue,
    CycleData,
    Data,
    KineticResult,
    Parameter,
    SystemInformation,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none, try_float_or_none


def _get_sensorgram_datacube(
    sensorgram_df: pd.DataFrame, *, cycle: int, flow_cell: str
) -> DataCube:
    # Extract all sensorgram data points
    time_vals = sensorgram_df["Time (s)"].astype(float).to_list()
    resp_vals = sensorgram_df["Sensorgram (RU)"].astype(float).to_list()
    return DataCube(
        label=f"Cycle{cycle}_FlowCell{flow_cell}",
        structure_dimensions=[
            DataCubeComponent(FieldComponentDatatype.double, "elapsed time", "s")
        ],
        structure_measures=[
            DataCubeComponent(FieldComponentDatatype.double, "resonance", "RU")
        ],
        dimensions=[time_vals],
        measures=[resp_vals],
    )


def create_metadata(data: Data, named_file_contents: NamedFileContents) -> Metadata:
    filepath = Path(named_file_contents.original_file_path)
    sys = data.system_information
    chip = data.chip_data
    # Fallback: if run metadata lacks compartment temp, try application_template_details.RackTemperature.value
    # Using the new bridge function that can handle both StrictXmlElement and dict
    rack_temp_val = _extract_value_from_xml_element_or_dict(
        (data.application_template_details or {}).get("RackTemperature", {})
    )
    # Additional fallback to system_preparations.RackTemp if present
    rack_temp_sys_prep = (
        (data.application_template_details or {}).get("system_preparations", {}) or {}
    ).get("RackTemp")
    compartment_temp = (
        data.run_metadata.compartment_temperature
        or try_float_or_none(rack_temp_val)
        or try_float_or_none(rack_temp_sys_prep)
    )

    return Metadata(
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_identifier=DEVICE_IDENTIFIER,
        asm_file_identifier=filepath.with_suffix(".json").name,
        model_number=MODEL_NUMBER,
        data_system_instance_identifier=sys.system_controller_identifier
        or NOT_APPLICABLE,
        file_name=filepath.name,
        unc_path=named_file_contents.original_file_path,
        software_name=sys.application_name,
        software_version=sys.application_version,
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=compartment_temp,
        sensor_chip_type=chip.sensor_chip_type,
        lot_number=chip.lot_number,
        sensor_chip_identifier=chip.sensor_chip_identifier,
        sensor_chip_custom_info=chip.custom_info,
        data_system_custom_info={
            "account identifier": sys.user_name,
            "operating system type": sys.os_type,
            "operating system version": sys.os_version,
            **sys.unread_application_properties,
        },
    )


def _extract_kinetic_parameter(
    kinetic_result: KineticResult | None, section: str, parameter_names: list[str]
) -> float | None:
    """Extract kinetic parameter value from KineticResult object."""
    if not kinetic_result:
        return None

    # Get the appropriate list based on section
    items: list[Parameter] | list[CalculatedValue]
    if section == "parameters":
        items = kinetic_result.parameters
    elif section == "calculated":
        items = kinetic_result.calculated
    else:
        return None

    # Search through the items for matching parameter names
    for item in items:
        if item.name.lower() in [name.lower() for name in parameter_names]:
            return float(item.value) if item.value is not None else None

    return None


def _extract_kinetic_parameter_error(
    kinetic_result: KineticResult | None, parameter_names: list[str]
) -> float | None:
    """Extract kinetic parameter error from KineticResult object."""
    if not kinetic_result:
        return None

    # Search through parameters for matching parameter names
    for item in kinetic_result.parameters:
        if item.name.lower() in [name.lower() for name in parameter_names]:
            return float(item.error) if item.error is not None else None

    return None


def _extract_chi2_value(kinetic_result: Any) -> float | None:
    """Extract Chi2 value from KineticResult fit quality."""
    if not kinetic_result or not kinetic_result.fit_quality:
        return None

    return (
        float(kinetic_result.fit_quality.chi2_value)
        if kinetic_result.fit_quality.chi2_value is not None
        else None
    )


def _create_report_point(
    series_data: SeriesData,
    flow_cell_id: str,
    cycle_number: int,
    display_flow_cell_id: str | None = None,
) -> ReportPoint | None:
    """Create a single ReportPoint object from SeriesData."""
    try:
        time_setting = series_data.get(float, ["column1", "Time"], default=0.0)
        relative_resonance = series_data.get(
            float, ["column3", "Relative"], default=0.0
        )
        identifier_role = series_data.get(str, ["column4", "Role"], default="baseline")
        absolute_resonance = series_data.get(
            float, ["column5", "Absolute"], default=0.0
        )

        unread_data = series_data.get_unread()

        fc_id_for_display = display_flow_cell_id or flow_cell_id
        report_point_id = f"CYTIVA_BIACORE_T200_EVALUATION_RP_C{cycle_number}_FC{fc_id_for_display}_{random_uuid_str()}"

        custom_info: dict[str, dict[str, object]] = {
            "window": {"value": 5.0, "unit": "s"}
        }
        for key, value in unread_data.items():
            custom_info[key] = {"value": value}

        return ReportPoint(
            identifier=report_point_id,
            identifier_role=identifier_role,
            absolute_resonance=absolute_resonance,
            time_setting=time_setting,
            relative_resonance=relative_resonance,
            custom_info=custom_info,
        )
    except Exception:
        series_data.get_unread()
        return None


def _create_report_points_from_cycle_data(
    rp_df: pd.DataFrame | None,
    flow_cell_id: str,
    cycle_number: int,
    display_flow_cell_id: str | None = None,
) -> list[ReportPoint] | None:
    """Create ReportPoint objects from cycle report point data, filtered by flow cell."""
    if rp_df is None or rp_df.empty:
        return None

    filtered_df = rp_df
    if "Flow Cell Number" in rp_df.columns or "flow_cell" in rp_df.columns:
        # Try to filter by flow cell
        fc_col = (
            "Flow Cell Number" if "Flow Cell Number" in rp_df.columns else "flow_cell"
        )
        # Convert flow_cell_id to match the format in the DataFrame
        try:
            fc_filter_value = int(flow_cell_id)
            filtered_df = rp_df[rp_df[fc_col] == fc_filter_value]
        except (ValueError, KeyError):
            # If filtering fails, use all data (fallback)
            filtered_df = rp_df

    report_points = [
        rp
        for rp in map_rows(
            filtered_df,
            lambda series_data: _create_report_point(
                series_data, flow_cell_id, cycle_number, display_flow_cell_id
            ),
        )
        if rp is not None
    ]

    return report_points if report_points else None


def _create_measurements_for_cycle(data: Data, cycle: CycleData) -> list[Measurement]:
    sensorgram_df = cycle.sensorgram_data
    cycle_num = cycle.cycle_number

    if "Flow Cell Number" not in sensorgram_df.columns:
        sensorgram_df["Flow Cell Number"] = 1
    if "Cycle Number" not in sensorgram_df.columns:
        sensorgram_df["Cycle Number"] = cycle_num

    rp_df: pd.DataFrame | None = cycle.report_point_data

    measurements: list[Measurement] = []

    def _normalize_flow_cell_id(value: Any) -> str:
        s = str(value)
        # Don't normalize reference-subtracted flow cell IDs (e.g., "2-1", "3-1", "4-1")
        if "-" in s:
            return s
        # Only normalize pure numeric flow cell IDs
        m = re.match(r"\d+", s)
        return m.group(0) if m else s

    # Process all flow cells (including reference-subtracted ones like "2-1", "3-1", "4-1")
    for flow_cell, df_fc in sensorgram_df.groupby("Flow Cell Number"):
        fc_id = _normalize_flow_cell_id(flow_cell)
        display_fc_id = (
            fc_id  # Use the flow cell ID (preserves reference-subtracted format)
        )

        # Extract report points from cycle data (use base fc_id for filtering data, display_fc_id for identifiers)
        report_points: list[ReportPoint] | None = _create_report_points_from_cycle_data(
            rp_df, fc_id, cycle_num, display_fc_id
        )

        device_control_custom_info: dict[str, Any] = {
            "buffer volume": quantity_or_none(
                TQuantityValueMilliliter, data.run_metadata.buffer_volume
            ),
            "detection": (
                data.run_metadata.detection_config.detection
                if data.run_metadata.detection_config
                else None
            ),
            "detectiondual": (
                data.run_metadata.detection_config.detection_dual
                if data.run_metadata.detection_config
                else None
            ),
            "detectionmulti": (
                data.run_metadata.detection_config.detection_multi
                if data.run_metadata.detection_config
                else None
            ),
            "flowcellsingle": (
                data.run_metadata.detection_config.flow_cell_single
                if data.run_metadata.detection_config
                else None
            ),
            "flowcelldual": (
                data.run_metadata.detection_config.flow_cell_dual
                if data.run_metadata.detection_config
                else None
            ),
            "flowcellmulti": (
                data.run_metadata.detection_config.flow_cell_multi
                if data.run_metadata.detection_config
                else None
            ),
            "maximum operating temperature": quantity_or_none(
                TQuantityValueDegreeCelsius, data.run_metadata.rack_temperature_max
            ),
            "minimum operating temperature": quantity_or_none(
                TQuantityValueDegreeCelsius, data.run_metadata.rack_temperature_min
            ),
            "analysis temperature": quantity_or_none(
                TQuantityValueDegreeCelsius, data.run_metadata.analysis_temperature
            ),
            "prime": str(bool(data.run_metadata.prime)).lower()
            if data.run_metadata.prime is not None
            else None,
            "normalize": str(bool(data.run_metadata.normalize)).lower()
            if data.run_metadata.normalize is not None
            else None,
        }

        # Add any unread detection data to device_control_custom_info
        if (
            data.run_metadata.detection_config
            and data.run_metadata.detection_config.unread_detection_data
        ):
            device_control_custom_info.update(
                data.run_metadata.detection_config.unread_detection_data
            )
        # Add experimental data identifier per measurement via chip immobilization mapping
        try:
            fc_index = int(str(fc_id))
        except Exception:
            fc_index = None
        if fc_index is not None:
            for imm in data.chip_data.immobilizations:
                if imm.flow_cell_index == fc_index and imm.ligand:
                    device_control_custom_info = {
                        **device_control_custom_info,
                        "ligand identifier": imm.ligand,
                    }
                if imm.flow_cell_index == fc_index and imm.level is not None:
                    device_control_custom_info = {
                        **device_control_custom_info,
                        "level": quantity_or_none(
                            TQuantityValueResponseUnit, imm.level
                        ),
                    }
                    break

        # Extract kinetic analysis data for this specific flow cell
        # Match EvaluationItem identifier to flow cell identifier
        combined_kinetic_data = None
        if data.kinetic_analysis and data.kinetic_analysis.results_by_identifier:
            # Try to find the specific EvaluationItem for this flow cell
            # Flow cell IDs are typically "1", "2", "3", "4"
            # EvaluationItem IDs are typically "EvaluationItem1", "EvaluationItem2", etc.
            matching_eval_item = None

            # First, try direct mapping: flow cell "1" -> "EvaluationItem1"
            eval_item_key = f"EvaluationItem{fc_id}"
            if eval_item_key in data.kinetic_analysis.results_by_identifier:
                matching_eval_item = eval_item_key
            else:
                # If direct mapping fails, look for any EvaluationItem that might correspond to this flow cell
                # This could be enhanced with more sophisticated matching logic if needed
                for eval_key in data.kinetic_analysis.results_by_identifier.keys():
                    if fc_id in eval_key or eval_key.endswith(fc_id):
                        matching_eval_item = eval_key
                        break

            # Use only the matching EvaluationItem data for this flow cell
            if matching_eval_item:
                result = data.kinetic_analysis.results_by_identifier[matching_eval_item]
                combined_kinetic_data = result

        kinetic_data = combined_kinetic_data

        measurements.append(
            Measurement(
                identifier=random_uuid_str(),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                sample_identifier=NOT_APPLICABLE,
                device_control_document=[
                    DeviceControlDocument(
                        device_type=constants.DEVICE_TYPE,
                        flow_cell_identifier=display_fc_id,
                        flow_rate=try_float_or_none(data.run_metadata.baseline_flow),
                        detection_type=constants.SURFACE_PLASMON_RESONANCE,
                        device_control_custom_info=device_control_custom_info,
                    )
                ],
                well_plate_identifier=(
                    (
                        (data.application_template_details or {}).get("racks", {}) or {}
                    ).get("_Rack1")
                ),
                sample_custom_info={
                    "rack2": (
                        (data.application_template_details or {}).get("racks", {}) or {}
                    ).get("_Rack2")
                },
                sensorgram_data_cube=_get_sensorgram_datacube(
                    df_fc, cycle=cycle_num, flow_cell=fc_id
                ),
                report_point_data=report_points,
                # Kinetic analysis fields
                binding_on_rate_measurement_datum__kon_=_extract_kinetic_parameter(
                    kinetic_data, "parameters", ["ka", "kon"]
                ),
                binding_off_rate_measurement_datum__koff_=_extract_kinetic_parameter(
                    kinetic_data, "parameters", ["kd", "koff"]
                ),
                equilibrium_dissociation_constant__kd_=_extract_kinetic_parameter(
                    kinetic_data, "calculated", ["Kd_M", "KD", "kd"]
                ),
                maximum_binding_capacity__rmax_=_extract_kinetic_parameter(
                    kinetic_data, "parameters", ["Rmax", "rmax"]
                ),
                # Attach custom kinetic analysis values for processed data custom info
                processed_data_custom_info={
                    "kinetics chi squared": {
                        "value": _extract_chi2_value(kinetic_data),
                        "unit": "(unitless)",
                    },
                    "ka error": {
                        "value": _extract_kinetic_parameter_error(
                            kinetic_data, ["ka", "kon"]
                        ),
                        "unit": "M-1s-1",
                    },
                    "kd error": {
                        "value": _extract_kinetic_parameter_error(
                            kinetic_data, ["kd", "koff"]
                        ),
                        "unit": "s^-1",
                    },
                    "Rmax error": {
                        "value": _extract_kinetic_parameter_error(
                            kinetic_data, ["Rmax", "rmax"]
                        ),
                        "unit": "RU",
                    },
                },
            )
        )

    return measurements


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    sys = data.system_information
    # Prefer application template timestamp if present in run metadata
    if data.run_metadata.timestamp and not sys.measurement_time:
        sys = SystemInformation(
            application_name=sys.application_name,
            application_version=sys.application_version,
            user_name=sys.user_name,
            system_controller_identifier=sys.system_controller_identifier,
            os_type=sys.os_type,
            os_version=sys.os_version,
            measurement_time=data.run_metadata.timestamp,
            unread_application_properties=sys.unread_application_properties,
            measurement_aggregate_fields=sys.measurement_aggregate_fields,
        )
    # As a final fallback, look directly in application_template_details.properties
    if not sys.measurement_time and data.application_template_details:
        props = data.application_template_details.get("properties", {})
        ts = props.get("Timestamp")
        if ts:
            sys = SystemInformation(
                application_name=sys.application_name,
                application_version=sys.application_version,
                user_name=sys.user_name,
                system_controller_identifier=sys.system_controller_identifier,
                os_type=sys.os_type,
                os_version=sys.os_version,
                measurement_time=ts,
                unread_application_properties=sys.unread_application_properties,
                measurement_aggregate_fields=sys.measurement_aggregate_fields,
            )
    if not sys.measurement_time:
        msg = "Missing measurement time. Expected application_template_details.properties.Timestamp."
        raise AllotropeParsingError(msg)
    groups: list[MeasurementGroup] = []
    # Process all cycles to create one measurement document per cycle
    for cycle in data.cycle_data:
        measurements = _create_measurements_for_cycle(data, cycle)
        custom_info: dict[str, Any] = {
            "data collection rate": quantity_or_none(
                TQuantityValueHertz, data.run_metadata.data_collection_rate
            ),
            **sys.measurement_aggregate_fields,
        }
        # Add aggregate-level experimental data identifier for convenience (first measurement's FC)
        if measurements:
            # Derive from first measurement's flow cell
            first_fc = measurements[0].device_control_document[0].flow_cell_identifier
            first_fc_str = str(first_fc)
            # Check if the flow cell identifier is a valid integer (skip reference-subtracted IDs like "2-1")
            if first_fc_str.isdigit():
                fc_index = int(first_fc_str)
                for imm in data.chip_data.immobilizations:
                    if imm.flow_cell_index == fc_index and imm.immob_file_path:
                        custom_info = {
                            **custom_info,
                            "experimental data identifier": imm.immob_file_path,
                        }
                        break

        groups.append(
            MeasurementGroup(
                measurement_time=sys.measurement_time,
                measurements=measurements,
                experiment_type=None,
                analytical_method_identifier=None,
                analyst=(
                    data.run_metadata.analyst or data.system_information.user_name
                ),
                measurement_aggregate_custom_info=custom_info,
            )
        )
    return groups


def create_data(
    named_file_contents: NamedFileContents,
) -> tuple[Metadata, list[MeasurementGroup]]:
    intermediate = decode_data(named_file_contents)
    data = Data.create(intermediate)
    metadata = create_metadata(data, named_file_contents)
    groups = create_measurement_groups(data)
    return metadata, groups
