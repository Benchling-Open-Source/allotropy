import os
from typing import Any

from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    DeviceDocument,
    MeasurementGroup,
    Measurements,
    MeasurementType,
    Metadata,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200_control import constants
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)


def create_metadata(
    intermediate_structured_data: dict[str, Any], named_file_contents: NamedFileContents
) -> Metadata:
    if (
        "sample_data"
        in intermediate_structured_data["application_template_details"].keys()
    ):
        compartment_temperature = intermediate_structured_data[
            "application_template_details"
        ]["RackTemperature"].get("Value")
    else:
        compartment_temperature = intermediate_structured_data[
            "application_template_details"
        ]["system_preparations"].get("RackTemp")
    return Metadata(
        brand_name=constants.BRAND_NAME,
        device_identifier=assert_not_none(
            intermediate_structured_data["system_information"].get("InstrumentId"),
            "InstrumentId",
        ),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        asm_file_identifier=f"{os.path.splitext(os.path.basename(named_file_contents.original_file_path))[0]}.json"
        if os.path.basename(named_file_contents.original_file_path)
        else "N/A",
        model_number=assert_not_none(
            intermediate_structured_data["system_information"].get("ProcessingUnit"),
            "ProcessingUnit",
        ),
        data_system_instance_identifier=NOT_APPLICABLE,
        file_name=os.path.basename(named_file_contents.original_file_path),
        unc_path=named_file_contents.original_file_path,
        software_name=intermediate_structured_data["system_information"].get(
            "Application"
        ),
        software_version=intermediate_structured_data["system_information"].get(
            "Version"
        ),
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=try_float_or_none(compartment_temperature)
        if compartment_temperature is not None
        else None,
        sensor_chip_type=intermediate_structured_data["chip"].get("Name"),
        lot_number=None
        if intermediate_structured_data["chip"].get("LotNo") == ""
        else intermediate_structured_data["chip"].get("LotNo"),
        sensor_chip_identifier=assert_not_none(
            intermediate_structured_data["chip"].get("Id"), "Chip ID"
        ),
        device_document=[
            DeviceDocument(
                device_type=key.split()[0], device_identifier=key.split()[-1]
            )
            for key in intermediate_structured_data["application_template_details"]
            if key.startswith("Flowcell")
        ]
        if any(
            key.startswith("Flowcell")
            for key in intermediate_structured_data["application_template_details"]
        )
        else None,
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
) -> list[Measurements]:
    if "sample_data" in intermediate_structured_data.keys():
        detection_setting = intermediate_structured_data[
            "application_template_details"
        ]["detection"]
        detection_type = detection_setting["Detection"]
        detection_key = f"Detection{detection_type}"
        detection_value = detection_setting[detection_key]
        return [
            Measurements(
                identifier=random_uuid_str(),
                sensorgram_posix_path=assert_not_none(
                    intermediate_structured_data["cycle_data"][i].get(
                        "sensorgram_path"
                    ),
                    "sensorgram path",
                ),
                sensorgram_posix_path_identifier=(
                    os.path.basename(
                        intermediate_structured_data["cycle_data"][i].get(
                            "sensorgram_path"
                        )
                    )
                    if intermediate_structured_data["cycle_data"][i].get(
                        "sensorgram_path"
                    )
                    is not None
                    else None
                ),
                rpoint_posix_path=intermediate_structured_data["cycle_data"][i].get(
                    "r-point_path"
                ),
                rpoint_posix_path_identifier=(
                    os.path.basename(
                        intermediate_structured_data["cycle_data"][i].get(
                            "r-point_path"
                        )
                    )
                    if intermediate_structured_data["cycle_data"][i].get("r-point_path")
                    is not None
                    else None
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type=constants.DEVICE_TYPE,
                sample_identifier=intermediate_structured_data["sample_data"][i].get(
                    "sample_name", NOT_APPLICABLE
                ),
                location_identifier=intermediate_structured_data["sample_data"][i].get(
                    "rack"
                ),
                sample_role_type=constants.PLATEMAP_TO_SAMPLE_ROLE_TYPE.get(intermediate_structured_data["sample_data"][i].get(
                    "role"
                )),
                concentration=try_float_or_none(
                    intermediate_structured_data["sample_data"][i].get("concentration")
                )
                if "concentration"
                in intermediate_structured_data["sample_data"][i].keys()
                else None,
                device_control_custom_info={
                    "number of flow cells": try_int_or_none(
                        intermediate_structured_data["chip"].get("NoFcs")
                    ),
                    "number of spots": try_int_or_none(
                        intermediate_structured_data["chip"].get("NoSpots")
                    ),
                    "buffer volume": {
                        "value": try_float_or_none(
                            next(
                                value
                                for key, value in intermediate_structured_data[
                                    "application_template_details"
                                ]["prepare_run"].items()
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
                            intermediate_structured_data["sample_data"][i].get(
                                "molecular_weight"
                            )
                        ),
                        "unit": "Da",
                    }
                },
            )
            for i in range(intermediate_structured_data["total_cycles"])
        ]
    else:
        return [
            Measurements(
                identifier=random_uuid_str(),
                sensorgram_posix_path=assert_not_none(
                    intermediate_structured_data["cycle_data"][i].get(
                        "sensorgram_path"
                    ),
                    "sensorgram path",
                ),
                sensorgram_posix_path_identifier=(
                    os.path.basename(
                        intermediate_structured_data["cycle_data"][i].get(
                            "sensorgram_path"
                        )
                    )
                    if intermediate_structured_data["cycle_data"][i].get(
                        "sensorgram_path"
                    )
                    is not None
                    else None
                ),
                rpoint_posix_path=intermediate_structured_data["cycle_data"][i].get(
                    "r-point_path"
                ),
                rpoint_posix_path_identifier=(
                    os.path.basename(
                        intermediate_structured_data["cycle_data"][i].get(
                            "r-point_path"
                        )
                    )
                    if intermediate_structured_data["cycle_data"][i].get("r-point_path")
                    is not None
                    else None
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                sample_identifier=intermediate_structured_data.get(
                    "sample_data", NOT_APPLICABLE
                ),
                method_name=intermediate_structured_data[
                    "application_template_details"
                ][f"Flowcell {i + 1}"].get("MethodName"),
                ligand_identifier=intermediate_structured_data[
                    "application_template_details"
                ][f"Flowcell {i + 1}"].get("Ligand"),
                flow_cell_identifier=f"Flowcell {i + 1}",
                flow_path=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ].get("DetectionText"),
                flow_rate=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ].get("Flow"),
                contact_time=intermediate_structured_data[
                    "application_template_details"
                ][f"Flowcell {i + 1}"].get("ContactTime"),
                dilution=try_int_or_none(
                    intermediate_structured_data["application_template_details"][
                        f"Flowcell {i + 1}"
                    ].get("DilutePercent")
                ),
                device_control_custom_info={
                    "number of flow cells": try_int_or_none(
                        intermediate_structured_data["chip"].get("NoFcs")
                    ),
                    "number of spots": try_int_or_none(
                        intermediate_structured_data["chip"].get("NoSpots")
                    ),
                    "buffer volume": {
                        "value": try_float_or_none(
                            next(
                                value
                                for key, value in intermediate_structured_data[
                                    "application_template_details"
                                ]["prepare_run"].items()
                                if key.startswith("Buffer")
                            )
                        ),
                        "unit": "mL",
                    },
                },
            )
            for i in range(intermediate_structured_data["total_cycles"])
        ]


def create_measurement_groups(
    intermediate_structured_data: dict[str, Any]
) -> MeasurementGroup:
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
        analyst=intermediate_structured_data["application_template_details"][
            "properties"
        ].get("User"),
        measurement_aggregate_custom_info={
            "baseline flow": {
                "value": try_float_or_none(
                    intermediate_structured_data["application_template_details"][
                        "BaselineFlow"
                    ].get("value")
                )
                if "BaselineFlow"
                in intermediate_structured_data["application_template_details"].keys()
                else None,
                "unit": "μL/min",
            },
            "data collection rate": {
                "value": try_float_or_none(
                    intermediate_structured_data["application_template_details"][
                        "DataCollectionRate"
                    ].get("value")
                )
                if "DataCollectionRate"
                in intermediate_structured_data["application_template_details"].keys()
                else None,
                "unit": "Hz",
            },
            "dip details": [
                {
                    "datum label": "norm_dip_details",
                    "datum value": norm_datum.get("response"),
                    "sweep row": norm_datum.get("sweep_row"),
                    "flow cell identifier": norm_datum.get("flow_cell"),
                }
                for norm_datum in intermediate_structured_data["dip"]["norm_data"]
            ]
            + [
                {
                    "datum label": "raw_dip_details",
                    "datum value": raw_datum.get("response"),
                    "sweep_row": raw_datum.get("sweep_row"),
                    "flow cell identifier": raw_datum.get("flow_cell"),
                }
                for raw_datum in intermediate_structured_data["dip"]["raw_data"]
            ],
        },
    )
