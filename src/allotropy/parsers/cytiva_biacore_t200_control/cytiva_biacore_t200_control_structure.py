from __future__ import annotations
from pathlib import Path
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueSecondTime,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    DeviceDocument,
    MeasurementGroup,
    Measurement,
    MeasurementType,
    Metadata,
    ReportPoint,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.utils.pandas import SeriesData, map_rows
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)


def _create_report_point(data: SeriesData) -> ReportPoint:
    return ReportPoint(
        identifier=random_uuid_str(),
        identifier_role=data[str, "Id"],
        absolute_response=data[float, "AbsResp"],
        relative_response=data.get(float, "RelResp"),
        time_setting=data[float, "Time"],
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


def _get_sensorgram_datacube(sensorgram_data: pd.DataFrame) -> DataCube:
    return DataCube(
        label="sensorgram",
        structure_dimensions=[
            DataCubeComponent(FieldComponentDatatype.double, "elapsed time", "s")
        ],
        structure_measures=[
            DataCubeComponent(FieldComponentDatatype.double, "response units", "RU")
        ],
        # TODO: Remove the slices! This is so it is easier to review the ASM result
        dimensions=[sensorgram_data["Time (s)"].astype(float).to_list()[:4]],
        measures=[sensorgram_data["Sensorgram (RU)"].astype(float).to_list()[:4]],
    )


def create_metadata(
    intermediate_structured_data: dict[str, Any], named_file_contents: NamedFileContents
) -> Metadata:
    filepath = Path(named_file_contents.original_file_path)
    application_template_details: dict[str, dict] = intermediate_structured_data[
        "application_template_details"
    ]
    system_information: dict = intermediate_structured_data["system_information"]

    compartment_temperature = (
        application_template_details["RackTemperature"].get("Value")
        if "sample_data" in application_template_details
        else application_template_details["system_preparations"].get("RackTemp")
    )

    return Metadata(
        brand_name=constants.BRAND_NAME,
        device_identifier=assert_not_none(
            system_information.get("InstrumentId"), "InstrumentId"
        ),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        asm_file_identifier=filepath.with_suffix(".json").name,
        model_number=assert_not_none(
            system_information.get("ProcessingUnit"), "ProcessingUnit"
        ),
        data_system_instance_identifier=NOT_APPLICABLE,
        file_name=filepath.name,
        unc_path=named_file_contents.original_file_path,
        software_name=system_information.get("Application"),
        software_version=system_information.get("Version"),
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=(
            try_float_or_none(compartment_temperature)
            if compartment_temperature is not None
            else None
        ),
        sensor_chip_type=intermediate_structured_data["chip"].get("Name"),
        lot_number=(
            None
            if intermediate_structured_data["chip"].get("LotNo") == ""
            else intermediate_structured_data["chip"].get("LotNo")
        ),
        sensor_chip_identifier=assert_not_none(
            intermediate_structured_data["chip"].get("Id"), "Chip ID"
        ),
        device_document=(
            [
                DeviceDocument(
                    device_type=key.split()[0], device_identifier=key.split()[-1]
                )
                for key in application_template_details
                if key.startswith("Flowcell")
            ]
            if any(key.startswith("Flowcell") for key in application_template_details)
            else None
        ),
        sensor_chip_custom_info={
            "ifc identifier": intermediate_structured_data["chip"].get("IFC"),
            "last modified time": intermediate_structured_data["chip"].get(
                "LastModTime"
            ),
            "last use time": intermediate_structured_data["chip"].get("LastUseTime"),
            "first dock date": intermediate_structured_data["chip"].get(
                "FirstDockDate"
            ),
        },
    )


def create_measurements(
    intermediate_structured_data: dict[str, Any]
) -> list[Measurement]:
    chip_data: dict = intermediate_structured_data["chip"]
    application_template_details: dict[str, dict] = intermediate_structured_data[
        "application_template_details"
    ]
    if "sample_data" in intermediate_structured_data:
        detection_setting = application_template_details["detection"]
        detection_type = detection_setting["Detection"]
        detection_key = f"Detection{detection_type}"
        detection_value = detection_setting[detection_key]
        measurements = []
        for idx in range(intermediate_structured_data["total_cycles"]):
            sample_data: dict = intermediate_structured_data["sample_data"][idx]
            cycle_data: dict[str, Any] = intermediate_structured_data["cycle_data"][idx]
            sensorgram_data: pd.DataFrame = cycle_data["sensorgram_data"]
            report_point_data: pd.DataFrame = cycle_data["report_point_data"]
            measurements.append(
                Measurement(
                    identifier=random_uuid_str(),
                    type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                    device_type=constants.DEVICE_TYPE,
                    sample_identifier=sample_data.get("sample_name", NOT_APPLICABLE),
                    location_identifier=sample_data.get("rack"),
                    sample_role_type=constants.SAMPLE_ROLE_TYPE.get(
                        sample_data.get("role")
                    ),
                    concentration=(
                        try_float_or_none(sample_data.get("concentration"))
                        if "concentration" in sample_data
                        else None
                    ),
                    flow_cell_identifier=str(
                        sensorgram_data.iloc[0]["Flow Cell Number"]
                    ),
                    device_control_custom_info={
                        "number of flow cells": try_int_or_none(chip_data.get("NoFcs")),
                        "number of spots": try_int_or_none(chip_data.get("NoSpots")),
                        "buffer volume": {
                            "value": try_float_or_none(
                                # TODO: refactor this. This seems unnecessary
                                next(
                                    value
                                    for key, value in application_template_details[
                                        "prepare_run"
                                    ].items()
                                    if key.startswith("Buffer")
                                )
                            ),
                            "unit": "mL",
                        },
                        **{detection_key.lower(): detection_value},
                    },
                    sample_custom_info={
                        "molecular weight": {
                            "value": try_float_or_none(
                                sample_data.get("molecular_weight")
                            ),
                            "unit": "Da",
                        }
                    },
                    # Sensorgram data
                    # TODO: add flow cell number
                    # sensorgram_flow_cell_identifier=str(
                    #     sensorgram_data.iloc[0]["Flow Cell Number"]
                    # ),
                    sensorgram_data_cube=_get_sensorgram_datacube(sensorgram_data),
                    # Report point data
                    # this is actually a list, one per row in the dataframe.
                    report_point_data=map_rows(report_point_data, _create_report_point),
                )
            )
        return measurements
    else:
        # Mobilization
        return [
            Measurement(
                identifier=random_uuid_str(),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                sample_identifier=NOT_APPLICABLE,
                method_name=application_template_details[f"Flowcell {i + 1}"].get(
                    "MethodName"
                ),
                ligand_identifier=application_template_details[f"Flowcell {i + 1}"].get(
                    "Ligand"
                ),
                # TODO: should we use the Flow cell number from the sensorgram instead?
                flow_cell_identifier=intermediate_structured_data["cycle_data"][i][
                    "sensorgram_data"
                ].iloc[0]["Flow Cell Number"],
                flow_path=application_template_details[f"Flowcell {i + 1}"].get(
                    "DetectionText"
                ),
                flow_rate=application_template_details[f"Flowcell {i + 1}"].get("Flow"),
                contact_time=application_template_details[f"Flowcell {i + 1}"].get(
                    "ContactTime"
                ),
                dilution=try_int_or_none(
                    application_template_details[f"Flowcell {i + 1}"].get(
                        "DilutePercent"
                    )
                ),
                device_control_custom_info={
                    "number of flow cells": try_int_or_none(chip_data.get("NoFcs")),
                    "number of spots": try_int_or_none(chip_data.get("NoSpots")),
                    "buffer volume": {
                        "value": try_float_or_none(
                            next(
                                value
                                for key, value in application_template_details[
                                    "prepare_run"
                                ].items()
                                if key.startswith("Buffer")
                            )
                        ),
                        "unit": "mL",
                    },
                },
                # Sensorgram data
                # TODO: add flow cell number
                # sensorgram_flow_cell_identifier=str(
                #     sensorgram_data.iloc[0]["Flow Cell Number"]
                # ),
                sensorgram_data_cube=_get_sensorgram_datacube(
                    intermediate_structured_data["cycle_data"][i]["sensorgram_data"]
                ),
                # Report point data
                # this is actually a list, one per row in the dataframe.
                report_point_data=map_rows(
                    intermediate_structured_data["cycle_data"][i]["report_point_data"],
                    _create_report_point,
                ),
            )
            for i in range(intermediate_structured_data["total_cycles"])
        ]


def create_measurement_groups(
    intermediate_structured_data: dict[str, Any]
) -> MeasurementGroup:
    application_template_details: dict[str, dict] = intermediate_structured_data[
        "application_template_details"
    ]
    return MeasurementGroup(
        measurement_time=assert_not_none(
            intermediate_structured_data["system_information"].get("Timestamp"),
            "Timestamp",
        ),
        measurements=create_measurements(intermediate_structured_data),
        experiment_type=intermediate_structured_data["system_information"].get(
            "RunTypeId"
        ),
        analytical_method_identifier=intermediate_structured_data[
            "system_information"
        ].get("TemplateFile"),
        analyst=application_template_details["properties"].get("User"),
        measurement_aggregate_custom_info={
            "baseline flow": {
                "value": (
                    try_float_or_none(
                        application_template_details["BaselineFlow"].get("value")
                    )
                    if "BaselineFlow" in application_template_details
                    else None
                ),
                "unit": "μL/min",
            },
            "data collection rate": {
                "value": (
                    try_float_or_none(
                        application_template_details["DataCollectionRate"].get("value")
                    )
                    if "DataCollectionRate" in application_template_details
                    else None
                ),
                "unit": "Hz",
            },
            # Note: Removed until we get more information on customer usage
            # "dip details": [
            #     {
            #         "datum label": "norm_dip_details",
            #         "datum value": norm_datum.get("response"),
            #         "sweep row": norm_datum.get("sweep_row"),
            #         "flow cell identifier": norm_datum.get("flow_cell"),
            #     }
            #     for norm_datum in intermediate_structured_data["dip"]["norm_data"]
            # ]
            # + [
            #     {
            #         "datum label": "raw_dip_details",
            #         "datum value": raw_datum.get("response"),
            #         "sweep_row": raw_datum.get("sweep_row"),
            #         "flow cell identifier": raw_datum.get("flow_cell"),
            #     }
            #     for raw_datum in intermediate_structured_data["dip"]["raw_data"]
            # ],
        },
    )
