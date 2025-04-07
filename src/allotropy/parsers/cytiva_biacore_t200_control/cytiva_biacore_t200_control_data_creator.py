from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDalton,
    TQuantityValueHertz,
    TQuantityValueMicroliterPerMinute,
    TQuantityValueMilliliter,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import ResonanceUnits, Unitless
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    DeviceDocument,
    Measurement,
    MeasurementGroup,
    Metadata,
    ReportPoint,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.cytiva_biacore_t200_control.extractor import (
    CytivaBiacoreExtractor,
)
from allotropy.calcdocs.cytiva_biacore_t200_control.views import ReportPointDataView
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_structure import (
    Data,
    MeasurementData,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import quantity_or_none, try_float_or_none
from allotropy.types import DictType


def _get_sensorgram_datacube(sensorgram_data: pd.DataFrame) -> DataCube:
    cycle = sensorgram_data.iloc[0]["Cycle Number"]
    flow_cell = sensorgram_data.iloc[0]["Flow Cell Number"]
    return DataCube(
        label=f"Cycle{cycle}_FlowCell{flow_cell}",
        structure_dimensions=[
            DataCubeComponent(FieldComponentDatatype.double, "elapsed time", "s")
        ],
        structure_measures=[
            DataCubeComponent(FieldComponentDatatype.double, "resonance", "RU")
        ],
        dimensions=[sensorgram_data["Time (s)"].astype(float).to_list()],
        measures=[sensorgram_data["Sensorgram (RU)"].astype(float).to_list()],
    )


def _get_device_control_custom_info(data: Data) -> DictType:
    custom_ifo: dict[str, Any] = {
        "number of flow cells": data.chip_data.number_of_flow_cells,
        "number of spots": data.chip_data.number_of_spots,
        "buffer volume": quantity_or_none(
            TQuantityValueMilliliter, data.run_metadata.buffer_volume
        ),
    }
    if detection_setting := data.run_metadata.detection_setting:
        custom_ifo.update({detection_setting.key: detection_setting.value})
    return custom_ifo


def create_metadata(data: Data, named_file_contents: NamedFileContents) -> Metadata:
    filepath = Path(named_file_contents.original_file_path)
    run_metadata = data.run_metadata
    system_information = data.system_information
    chip_data = data.chip_data

    return Metadata(
        brand_name=constants.BRAND_NAME,
        device_identifier=system_information.device_identifier,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        asm_file_identifier=filepath.with_suffix(".json").name,
        model_number=system_information.model_number,
        data_system_instance_identifier=NOT_APPLICABLE,
        file_name=filepath.name,
        unc_path=named_file_contents.original_file_path,
        software_name=system_information.software_name,
        software_version=system_information.software_version,
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=run_metadata.compartment_temperature,
        sensor_chip_type=chip_data.sensor_chip_type,
        lot_number=chip_data.lot_number,
        sensor_chip_identifier=chip_data.sensor_chip_identifier,
        device_document=[
            DeviceDocument(device.type_, device.identifier)
            for device in run_metadata.devices
        ],
        sensor_chip_custom_info=chip_data.custom_info,
    )


def create_measurements(
    measurements_data: list[MeasurementData], device_control_custom_info: DictType
) -> list[Measurement]:
    return [
        Measurement(
            identifier=measurement.identifier,
            type_=measurement.type_,
            device_type=measurement.device_type,
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
            sample_role_type=measurement.sample_role_type,
            concentration=measurement.concentration,
            flow_cell_identifier=measurement.flow_cell_identifier,
            device_control_custom_info=device_control_custom_info,
            sample_custom_info={
                "molecular weight": quantity_or_none(
                    TQuantityValueDalton, measurement.molecular_weight
                )
            },
            sensorgram_data_cube=_get_sensorgram_datacube(measurement.sensorgram_data),
            report_point_data=(
                [
                    ReportPoint(
                        identifier=rp_data.identifier,
                        identifier_role=rp_data.identifier_role,
                        absolute_resonance=rp_data.absolute_resonance,
                        relative_resonance=rp_data.relative_resonance,
                        time_setting=rp_data.time_setting,
                        custom_info=rp_data.custom_info,
                    )
                    for rp_data in measurement.report_point_data
                ]
                if measurement.report_point_data is not None
                else None
            ),
            # for Mobilization experiments
            method_name=measurement.method_name,
            ligand_identifier=measurement.ligand_identifier,
            flow_path=measurement.flow_path,
            flow_rate=measurement.flow_rate,
            contact_time=measurement.contact_time,
            dilution=measurement.dilution,
        )
        for measurement in measurements_data
    ]


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    system_information = data.system_information
    device_control_custom_info = _get_device_control_custom_info(data)
    return [
        MeasurementGroup(
            measurement_time=system_information.measurement_time,
            measurements=create_measurements(
                measurements_data, device_control_custom_info
            ),
            experiment_type=system_information.experiment_type,
            analytical_method_identifier=system_information.analytical_method_identifier,
            analyst=data.run_metadata.analyst,
            measurement_aggregate_custom_info={
                "baseline flow": quantity_or_none(
                    TQuantityValueMicroliterPerMinute, data.run_metadata.baseline_flow
                ),
                "data collection rate": quantity_or_none(
                    TQuantityValueHertz,
                    try_float_or_none(data.run_metadata.data_collection_rate),
                ),
            },
        )
        for measurements_data in data.sample_data.measurements.values()
    ]


def create_calculated_data(data: Data) -> list[CalculatedDocument]:
    report_point_data_view = ReportPointDataView().apply(
        CytivaBiacoreExtractor.sample_data_to_elements(data.sample_data)
    )
    absolute_resonance_conf = MeasurementConfig(
        name="Absolute Resonance",
        value="absolute_resonance",
    )

    configs = CalcDocsConfig(
        [
            CalculatedDataConfig(
                name="Min Resonance",
                value="min_resonance",
                view_data=report_point_data_view,
                source_configs=(absolute_resonance_conf,),
                unit=ResonanceUnits.unit,
            ),
            CalculatedDataConfig(
                name="Max Resonance",
                value="max_resonance",
                view_data=report_point_data_view,
                source_configs=(absolute_resonance_conf,),
                unit=ResonanceUnits.unit,
            ),
            CalculatedDataConfig(
                name="LRSD",
                value="lrsd",
                view_data=report_point_data_view,
                source_configs=(absolute_resonance_conf,),
                unit=Unitless.unit,
            ),
            CalculatedDataConfig(
                name="Slope",
                value="slope",
                view_data=report_point_data_view,
                source_configs=(absolute_resonance_conf,),
                unit=Unitless.unit,
            ),
            CalculatedDataConfig(
                name="SD",
                value="sd",
                view_data=report_point_data_view,
                source_configs=(absolute_resonance_conf,),
                unit=Unitless.unit,
            ),
        ]
    )

    return [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]
