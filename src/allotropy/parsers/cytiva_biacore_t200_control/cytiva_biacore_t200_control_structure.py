from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueSecondTime,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    MeasurementType,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)
from allotropy.types import DictType


@dataclass(frozen=True)
class ChipData:
    sensor_chip_identifier: str
    sensor_chip_type: str | None
    number_of_flow_cells: int | None
    number_of_spots: int | None
    lot_number: str | None
    custom_info: DictType

    @staticmethod
    def create(chip_data: DictType) -> ChipData:
        return ChipData(
            sensor_chip_identifier=assert_not_none(chip_data.get("Id"), "Chip ID"),
            sensor_chip_type=chip_data.get("Name"),
            number_of_flow_cells=try_int_or_none(chip_data.get("NoFcs")),
            number_of_spots=try_int_or_none(chip_data.get("NoSpots")),
            lot_number=lot_no if (lot_no := chip_data.get("LotNo")) else None,
            custom_info={
                "ifc identifier": chip_data.get("IFC"),
                "last modified time": chip_data.get("LastModTime"),
                "last use time": chip_data.get("LastUseTime"),
                "first dock date": chip_data.get("FirstDockDate"),
            },
        )


@dataclass(frozen=True)
class DetectionSetting:
    key: str
    value: float

    @staticmethod
    def create(detection_setting: DictType) -> DetectionSetting:
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
        application_template_details: dict[str, DictType] | None,
    ) -> RunMetadata:
        if application_template_details is None:
            return RunMetadata()
        return RunMetadata(
            analyst=application_template_details["properties"].get("User"),
            compartment_temperature=try_float_or_none(
                application_template_details["RackTemperature"].get("Value")
                if "sample_data" in application_template_details
                else application_template_details["system_preparations"].get("RackTemp")
            ),
            baseline_flow=try_float_or_none(
                application_template_details.get("BaselineFlow", {}).get("value")
            ),
            data_collection_rate=try_float_or_none(
                application_template_details.get("DataCollectionRate", {}).get("value")
            ),
            detection_setting=(
                DetectionSetting.create(detection_setting)
                if (detection_setting := application_template_details.get("detection"))
                else None
            ),
            buffer_volume=try_float_or_none(
                next(
                    value
                    for key, value in application_template_details[
                        "prepare_run"
                    ].items()
                    if key.startswith("Buffer")
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
    def create(system_information: DictType) -> SystemInformation:
        return SystemInformation(
            device_identifier=assert_not_none(
                system_information.get("InstrumentId"), "InstrumentId"
            ),
            model_number=assert_not_none(
                system_information.get("ProcessingUnit"), "ProcessingUnit"
            ),
            measurement_time=assert_not_none(
                system_information.get("Timestamp"), "Timestamp"
            ),
            experiment_type=system_information.get("RunTypeId"),
            analytical_method_identifier=system_information.get("TemplateFile"),
            software_name=system_information.get("Application"),
            software_version=system_information.get("Version"),
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


@dataclass(frozen=True)
class SampleData:
    measurements: dict[str, list[MeasurementData]]

    @staticmethod
    def create(intermediate_structured_data: DictType) -> SampleData:
        application_template_details: dict[
            str, DictType
        ] = intermediate_structured_data.get("application_template_details", {})
        measurements: dict[str, list[MeasurementData]] = defaultdict(list)
        for idx in range(intermediate_structured_data["total_cycles"]):
            flowcell_cycle_data: DictType = application_template_details.get(
                f"Flowcell {idx + 1}", {}
            )
            sample_data: DictType = (
                sd[idx]
                if (sd := intermediate_structured_data.get("sample_data"))
                else {}
            )
            cycle_data: DictType = intermediate_structured_data["cycle_data"][idx]
            sensorgram_data: pd.DataFrame = cycle_data["sensorgram_data"]
            # some experiments don't have report point data for some cycles (apparently just the first one)
            report_point_data: pd.DataFrame | None = cycle_data["report_point_data"]

            sample_identifier = sample_data.get("sample_name", NOT_APPLICABLE)
            location_identifier = sample_data.get("rack")
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
                        sample_data.get("role", "__IVALID_KEY__")
                    ),
                    concentration=try_float_or_none(sample_data.get("concentration")),
                    molecular_weight=try_float_or_none(
                        sample_data.get("molecular_weight")
                    ),
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
                    method_name=flowcell_cycle_data.get("MethodName"),
                    ligand_identifier=flowcell_cycle_data.get("Ligand"),
                    flow_path=flowcell_cycle_data.get("DetectionText"),
                    flow_rate=try_float_or_none(flowcell_cycle_data.get("Flow")),
                    contact_time=try_float_or_none(
                        flowcell_cycle_data.get("ContactTime")
                    ),
                    dilution=try_float_or_none(
                        flowcell_cycle_data.get("DilutePercent")
                    ),
                )
                # group sensorgram data by Flow Cell Number (Fc in rpoint data)
                for flow_cell, sensorgram_df in sensorgram_data.groupby(
                    "Flow Cell Number"
                )
            ]
        return SampleData(measurements)


@dataclass(frozen=True)
class Data:
    run_metadata: RunMetadata
    chip_data: ChipData
    system_information: SystemInformation
    sample_data: SampleData

    @staticmethod
    def create(intermediate_structured_data: DictType) -> Data:
        application_template_details: dict[
            str, DictType
        ] | None = intermediate_structured_data.get("application_template_details")
        chip_data: DictType = intermediate_structured_data["chip"]
        system_information: DictType = intermediate_structured_data[
            "system_information"
        ]
        return Data(
            run_metadata=RunMetadata.create(application_template_details),
            chip_data=ChipData.create(chip_data),
            system_information=SystemInformation.create(system_information),
            sample_data=SampleData.create(intermediate_structured_data),
        )
