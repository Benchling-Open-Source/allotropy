from pathlib import Path
from typing import Any

import numpy as np

from allotropy.allotrope.models.shared.definitions.quantity_values import (
    TQuantityValueHz,
    TQuantityValueNumberSign,
    TQuantityValueRU,
    TQuantityValueRUSq,
    TQuantityValueS,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.units import (
    ResponseUnitPerSecond,
    Unitless,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ReportPoint,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_insight import constants
from allotropy.parsers.cytiva_biacore_insight.cytiva_biacore_insight_structure import (
    BiacoreInsightMetadata,
    Data,
    MeasurementData,
    ReportPointData,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none


def _clean_custom_info(custom_info: dict[str, Any]) -> dict[str, Any]:
    """Remove None and NaN values from custom_info dictionaries."""

    def is_valid_value(value: Any) -> bool:
        if value is None:
            return False
        # Check for NaN in plain float values
        if isinstance(value, float) and np.isnan(value):
            return False
        # Check for NaN in quantity objects (objects with 'value' attribute or dicts with 'value' key)
        if hasattr(value, "value"):
            val = value.value
            if isinstance(val, float) and np.isnan(val):
                return False
        elif isinstance(value, dict) and "value" in value:
            val = value["value"]
            if isinstance(val, float) and np.isnan(val):
                return False
        return True

    return {key: value for key, value in custom_info.items() if is_valid_value(value)}


def create_metadata(metadata: BiacoreInsightMetadata, file_path: str) -> Metadata:
    path = Path(file_path)
    run_metadata = metadata.runs[0]
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
        model_number=run_metadata.model_number,
        sensor_chip_identifier=run_metadata.sensor_chip_id,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=metadata.software_name,
        software_version=metadata.software_version,
        file_name=metadata.file_name,
        unc_path=metadata.unc_path,
        detection_type=constants.DETECTION_TYPE,
        equipment_serial_number=run_metadata.equipment_serial_number,
        compartment_temperature=run_metadata.compartment_temperature,
        sensor_chip_type=run_metadata.sensor_chip_type,
        lot_number=run_metadata.lot_number,
    )


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    # Here we assume that the first run contains the relevant metadata for the measurement group.
    run_metadata = data.metadata.runs[0]
    return [
        MeasurementGroup(
            measurement_time=run_metadata.measurement_time,
            analytical_method_identifier=data.metadata.analytical_method_id,
            analyst=data.metadata.analyst,
            measurement_aggregate_custom_info={
                "number_of_cycles": TQuantityValueNumberSign(
                    value=run_metadata.number_of_cycles
                ),
                "data_collection_rate": TQuantityValueHz(
                    value=run_metadata.data_collection_rate
                ),
                "running_buffer": run_metadata.running_buffer,
                "measurement_end_time": run_metadata.measurement_end_time,
            },
            measurements=_get_measurements(cycle_measurements, data.metadata),
        )
        for cycle_measurements in data.cycles.values()
    ]


def _get_measurements(
    measurement_data: list[MeasurementData], metadata: BiacoreInsightMetadata
) -> list[Measurement]:
    data_processing_document = dict(metadata.data_processing_document or {})

    return [
        Measurement(
            identifier=measurement.identifier,
            sample_identifier=measurement.sample_identifier,
            type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
            method_name=measurement.method_name,
            ligand_identifier=measurement.ligand_identifier,
            device_control_document=measurement.device_control_document,
            sample_custom_info=measurement.sample_custom_info,
            binding_on_rate_measurement_datum__kon_=(
                measurement.kinetics.binding_on_rate_measurement_datum
            ),
            binding_off_rate_measurement_datum__koff_=(
                measurement.kinetics.binding_off_rate_measurement_datum
            ),
            equilibrium_dissociation_constant__kd_=(
                measurement.kinetics.equilibrium_dissociation_constant
            ),
            maximum_binding_capacity__rmax_=(
                measurement.kinetics.maximum_binding_capacity
            ),
            processed_data_custom_info=_clean_custom_info(
                {
                    (
                        "Affinity Chi squared"
                        if measurement.kinetics.is_affinity_measurement
                        else "Kinetics Chi squared"
                    ): quantity_or_none(
                        TQuantityValueRUSq,
                        measurement.kinetics.kinetics_chi_squared,
                    ),
                    "tc": quantity_or_none(
                        TQuantityValueUnitless, measurement.kinetics.tc
                    ),
                    "offset": quantity_or_none(
                        TQuantityValueRU,
                        measurement.kinetics.offset,
                    ),
                }
            ),
            report_point_data=[
                ReportPoint(
                    identifier=rp.identifier,
                    identifier_role=rp.identifier_role,
                    absolute_resonance=rp.absolute_resonance,
                    time_setting=rp.time_setting,
                    relative_resonance=rp.relative_resonance,
                    custom_info=_clean_custom_info(
                        {
                            "Step purpose": rp.step_purpose,
                            "Window": quantity_or_none(TQuantityValueS, rp.window),
                            "Baseline": rp.baseline,
                        }
                    ),
                )
                for rp in measurement.report_point_data
            ],
            data_processing_document=_clean_custom_info(
                {
                    **data_processing_document,
                    "Acceptance State": measurement.kinetics.acceptance_state,
                    "Curve Markers": measurement.kinetics.curve_markers,
                    "Kinetics Model": measurement.kinetics.kinetics_model,
                }
            ),
        )
        for measurement in measurement_data
    ]


def create_calculated_data(data: Data) -> list[CalculatedDocument]:
    calculated_data = []
    for cycle_measurements in data.cycles.values():
        for measurement in cycle_measurements:
            for rp in measurement.report_point_data:
                calculated_data.extend(_get_report_point_calc_data(rp))

    return calculated_data


def _get_report_point_calc_data(rp: ReportPointData) -> list[CalculatedDocument]:
    calc_data = []
    data_source = DataSource(
        feature="Absolute Response", reference=Referenceable(rp.identifier)
    )
    if rp.lrsd is not None:
        calc_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name="LRSD",
                value=rp.lrsd,
                data_sources=[data_source],
                unit=Unitless.unit,
            )
        )
    if rp.slope is not None:
        calc_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name="Slope",
                value=rp.slope,
                data_sources=[data_source],
                unit=ResponseUnitPerSecond.unit,
            )
        )
    if rp.standard_deviation is not None:
        calc_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name="Standard deviation",
                value=rp.standard_deviation,
                data_sources=[data_source],
                unit=Unitless.unit,
            )
        )
    return calc_data
