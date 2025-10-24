from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueSecondTime,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    MeasurementType,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.utils.dict_data import DictData
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
)
from allotropy.types import DictType


@dataclass(frozen=True)
class ChipData:
    sensor_chip_identifier: str
    sensor_chip_type: str | None
    number_of_flow_cells: int | None
    number_of_spots: int | None
    lot_number: str | None
    custom_info: dict[str, Any]

    @staticmethod
    def create(chip_data: DictData) -> ChipData:
        return ChipData(
            sensor_chip_identifier=assert_not_none(chip_data.get(str, "Id"), "Chip ID"),
            sensor_chip_type=chip_data.get(str, "Name"),
            number_of_flow_cells=chip_data.get(int, "NoFcs"),
            number_of_spots=chip_data.get(int, "NoSpots"),
            lot_number=lot_no if (lot_no := chip_data.get(str, "LotNo")) else None,
            custom_info={
                "ifc identifier": chip_data.get(str, "IFC"),
                "last modified time": chip_data.get(str, "LastModTime"),
                "last use time": chip_data.get(str, "LastUseTime"),
                "first dock date": chip_data.get(str, "FirstDockDate"),
            },
        )


@dataclass(frozen=True)
class DetectionSetting:
    key: str
    value: float | None

    @staticmethod
    def create(detection_setting: DictData) -> DetectionSetting:
        detection_key = f"Detection{detection_setting['Detection']}"
        return DetectionSetting(
            key=detection_key.lower(),
            value=detection_setting[detection_key],
        )


@dataclass(frozen=True)
class Device:
    type_: str
    identifier: str


@dataclass(frozen=True)
class RunMetadata:
    analyst: str | None = None
    compartment_temperature: float | None = None
    baseline_flow: float | None = None
    data_collection_rate: float | None = None
    detection_setting: DetectionSetting | None = None
    buffer_volume: float | None = None
    devices: list[Device] = field(default_factory=list)

    @staticmethod
    def create(
        application_template_details: DictData | None,
    ) -> RunMetadata:
        if application_template_details is None:
            return RunMetadata()
        baseline_flow = application_template_details.get_nested("BaselineFlow")
        baseline_flow_value = baseline_flow.get("value")
        data_collection_rate = application_template_details.get_nested(
            "DataCollectionRate"
        )
        data_collection_rate_value = data_collection_rate.get("value")
        return RunMetadata(
            analyst=application_template_details.get(
                DictData, "properties", DictData({})
            ).get(str, "User"),
            compartment_temperature=try_float_or_none(
                application_template_details.get_nested("RackTemperature")["Value"]
                if "sample_data" in application_template_details
                else application_template_details.get(
                    DictData,
                    "system_preparations",
                    DictData({}),
                ).get(str, "RackTemp")
            ),
            baseline_flow=try_float_or_none(baseline_flow_value),
            data_collection_rate=try_float_or_none(data_collection_rate_value),
            detection_setting=(
                DetectionSetting.create(
                    application_template_details.get_nested("detection")
                )
                if application_template_details.get_nested("detection")
                else None
            ),
            buffer_volume=try_float_or_none(
                next(
                    (
                        value
                        for key, value in application_template_details.get_nested(
                            "prepare_run"
                        ).items()
                        if key.startswith("Buffer")
                    ),
                    None,
                )
            ),
            devices=[
                Device(type_=key.split()[0], identifier=key.split()[-1])
                for key in application_template_details
                if key.startswith("Flowcell")
            ],
        )


@dataclass(frozen=True)
class SystemInformation:
    device_identifier: str
    model_number: str
    measurement_time: str
    experiment_type: str | None
    analytical_method_identifier: str | None
    software_name: str | None
    software_version: str | None

    @staticmethod
    def create(system_information: DictData) -> SystemInformation:
        return SystemInformation(
            device_identifier=assert_not_none(
                system_information.get(str, "InstrumentId"), "InstrumentId"
            ),
            model_number=assert_not_none(
                system_information.get(str, "ProcessingUnit"),
                "ProcessingUnit",
            ),
            measurement_time=assert_not_none(
                system_information.get(str, "Timestamp"), "Timestamp"
            ),
            experiment_type=system_information.get(str, "RunTypeId"),
            analytical_method_identifier=system_information.get(str, "TemplateFile"),
            software_name=system_information.get(str, "Application"),
            software_version=system_information.get(str, "Version"),
        )


@dataclass(frozen=True)
class ReportPointData:
    identifier: str
    identifier_role: str
    absolute_resonance: float
    relative_resonance: float | None
    time_setting: float
    custom_info: DictType
    min_resonance: float
    max_resonance: float
    lrsd: float
    slope: float
    sd: float

    @staticmethod
    def create(data: SeriesData) -> ReportPointData:
        return ReportPointData(
            identifier=random_uuid_str(),
            identifier_role=data[str, "Id"],
            absolute_resonance=data[float, "AbsResp"],
            relative_resonance=data.get(float, "RelResp"),
            time_setting=data[float, "Time"],
            min_resonance=data[float, "Min"],
            max_resonance=data[float, "Max"],
            lrsd=data[float, "LRSD"],
            slope=data[float, "Slope"],
            sd=data[float, "SD"],
            custom_info={
                "diode_row": data.get(str, "DiodeRow"),
                "window": (
                    TQuantityValueSecondTime(value=window)
                    if (window := data.get(float, "Window")) is not None
                    else None
                ),
                "quality": data.get(str, "Quality"),
                "baseline": data.get(str, "Baseline"),
                "assay_step": data.get(str, "AssayStep"),
                "assay_step_purpose": data.get(str, "AssayStepPurpose"),
                "buffer": data.get(str, "Buffer"),
            },
        )


@dataclass(frozen=True)
class MeasurementData:
    identifier: str
    type_: MeasurementType
    device_type: str
    sample_identifier: str
    flow_cell_identifier: str
    sensorgram_data: pd.DataFrame
    report_point_data: list[ReportPointData] | None
    location_identifier: str | None
    sample_role_type: str | None
    concentration: float | None
    molecular_weight: float | None
    # for Mobilization experiments
    method_name: str | None
    ligand_identifier: str | None
    flow_path: str | None
    flow_rate: float | None
    contact_time: float | None
    dilution: float | None
    custom_info: dict[str, Any]


@dataclass(frozen=True)
class SampleData:
    measurements: dict[str, list[MeasurementData]]
    custom_info: dict[str, Any]

    @staticmethod
    def create(intermediate_structured_data: DictData) -> SampleData:
        application_template_details = intermediate_structured_data.get_nested(
            "application_template_details"
        )
        measurements: dict[str, list[MeasurementData]] = defaultdict(list)
        total_cycles = assert_not_none(
            intermediate_structured_data.get(int, "total_cycles"),
            "total_cycles",
        )
        for idx in range(total_cycles):
            flowcell_cycle_json = application_template_details.get_nested(
                f"Flowcell {idx + 1}"
            )
            sd_list = intermediate_structured_data.get(list, "sample_data", [])
            sample_data_json = sd_list[idx] if sd_list else DictData({})

            cycle_data_list = intermediate_structured_data.get(list, "cycle_data", [])
            cycle_data: dict[str, pd.DataFrame] = cycle_data_list[idx]
            sensorgram_data: pd.DataFrame = cycle_data["sensorgram_data"]
            # some experiments don't have report point data for some cycles (apparently just the first one)
            report_point_data: pd.DataFrame | None = cycle_data["report_point_data"]

            sample_identifier = sample_data_json.get(str, "sample_name", NOT_APPLICABLE)
            location_identifier = sample_data_json.get(str, "rack")
            sample_location_key = f"{location_identifier}_{sample_identifier}"

            # Measurements are grouped by sample and location identifiers
            measurements[sample_location_key] += [
                MeasurementData(
                    identifier=random_uuid_str(),
                    type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                    device_type=constants.DEVICE_TYPE,
                    sample_identifier=sample_identifier,
                    flow_cell_identifier=str(flow_cell),
                    location_identifier=location_identifier,
                    sample_role_type=constants.SAMPLE_ROLE_TYPE.get(
                        sample_data_json.get(str, "role", "__IVALID_KEY__")
                    ),
                    concentration=sample_data_json.get(float, "concentration"),
                    molecular_weight=sample_data_json.get(float, "molecular_weight"),
                    sensorgram_data=sensorgram_df,
                    report_point_data=(
                        map_rows(
                            report_point_data[report_point_data["Fc"] == flow_cell],
                            ReportPointData.create,
                        )
                        if report_point_data is not None
                        else None
                    ),
                    # for Mobilization experiments
                    method_name=flowcell_cycle_json.get(str, "MethodName"),
                    ligand_identifier=flowcell_cycle_json.get(str, "Ligand"),
                    flow_path=flowcell_cycle_json.get(str, "DetectionText"),
                    flow_rate=flowcell_cycle_json.get(float, "Flow"),
                    contact_time=flowcell_cycle_json.get(float, "ContactTime"),
                    dilution=flowcell_cycle_json.get(float, "DilutePercent"),
                    custom_info={},
                )
                # group sensorgram data by Flow Cell Number (Fc in rpoint data)
                for flow_cell, sensorgram_df in sensorgram_data.groupby(
                    "Flow Cell Number"
                )
            ]
        custom_info: dict[str, Any] = {}
        return SampleData(measurements, custom_info)


@dataclass(frozen=True)
class Data:
    run_metadata: RunMetadata
    chip_data: ChipData
    system_information: SystemInformation
    sample_data: SampleData

    @staticmethod
    def create(intermediate_structured_data: DictData) -> Data:
        application_template_details = intermediate_structured_data.get_nested(
            "application_template_details"
        )
        chip_data = intermediate_structured_data.get_nested("chip")
        system_information = intermediate_structured_data.get_nested(
            "system_information"
        )

        return Data(
            run_metadata=RunMetadata.create(application_template_details),
            chip_data=ChipData.create(chip_data),
            system_information=SystemInformation.create(system_information),
            sample_data=SampleData.create(intermediate_structured_data),
        )
