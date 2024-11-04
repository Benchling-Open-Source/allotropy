import os
from typing import Any

from allotropy.allotrope.schema_mappers.adm.binding_affinity_analyzer.benchling._2024._12.binding_affinity_analyzer import (
    Data,
    DeviceDocument,
    MeasurementGroup,
    Measurements,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.utils.values import try_float, try_int_or_none,try_float_or_none
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200 import constants
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(
    intermediate_structured_data: dict[str, Any], named_file_contents: NamedFileContents
) -> Metadata:
    if "sample_data" in intermediate_structured_data["application_template_details"].keys():
        compartment_temperature = (
            intermediate_structured_data["application_template_details"]["RackTemperature"]
            .get("Value", None)
        )
    else:
        compartment_temperature = intermediate_structured_data["application_template_details"][
            "system_preparations"
        ]["RackTemp"]
    return Metadata(
        brand_name=constants.BRAND_NAME,
        device_identifier=intermediate_structured_data["system_information"]["InstrumentId"],
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        model_number=constants.MODEL_NUMBER,
        file_name=named_file_contents.original_file_path,
        unc_path=named_file_contents.contents.name,
        software_name=intermediate_structured_data["system_information"].get(
            "Application", None
        ),
        software_version=intermediate_structured_data["system_information"].get("Version", None),
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=try_float_or_none(compartment_temperature)
        if compartment_temperature is not None
        else None,
        sensor_chip_type=intermediate_structured_data["chip"].get("Name", None),
        sensor_chip_identifier=intermediate_structured_data["chip"].get("Id", None),
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
            "ifc identifier": intermediate_structured_data["chip"].get("IFC", None),
            "lot number": try_int_or_none(intermediate_structured_data["chip"].get("LotNo", None)),
            "last modified_time": intermediate_structured_data["chip"].get("LastModTime", None),
            "last use time": intermediate_structured_data["chip"].get("LastUseTime", None),
            "first dock date": intermediate_structured_data["chip"].get("FirstDockDate", None),
        },
    )


def  create_measurements(intermediate_structured_data: dict[str, Any]) -> list[Measurements]:
    if "sample_data" in intermediate_structured_data.keys():
        detection_setting = intermediate_structured_data["application_template_details"]["detection"]
        detection_type = detection_setting["Detection"]
        detection_key = f"Detection{detection_type}"
        detection_value = detection_setting[detection_key]
        return [
            Measurements(
                identifier=random_uuid_str(),
                sensorgram_posix_path=intermediate_structured_data["cycle_data"][i]["sensorgram_path"],
                sensorgram_posix_path_identifier=os.path.basename(
                    intermediate_structured_data["cycle_data"][i]["sensorgram_path"]
                ),
                rpoint_posix_path=intermediate_structured_data["cycle_data"][i]["r-point_path"],
                rpoint_posix_path_identifier=os.path.basename(
                    intermediate_structured_data["cycle_data"][i]["r-point_path"]
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                well_plate_identifier=intermediate_structured_data["application_template_details"][
                    "racks"
                ],
                sample_identifier=intermediate_structured_data["sample_data"][i].get(
                    "sample_name", NOT_APPLICABLE
                ),
                location_identifier=intermediate_structured_data["sample_data"][i]["rack"],
                sample_role_type=intermediate_structured_data["sample_data"][i]["role"],
                concentration=float(intermediate_structured_data["sample_data"][i].get("concentration"))
                if "concentration" in intermediate_structured_data["sample_data"][i].keys()
                else None,
                device_control_custom_info={
                    "number of flow cells": intermediate_structured_data["chip"].get("NoFcs", None),
                    "number of spots": intermediate_structured_data["chip"].get("NoSpots", None),
                    "buffer volume": {
                        "value": next(
                            value
                            for key, value in intermediate_structured_data["application_template_details"][
                                "prepare_run"
                            ].items()
                            if key.startswith("Buffer")
                        ),
                        "unit": "mL",
                    },
                    **{detection_key.lower(): detection_value},
                },
                sample_custom_info={
                    "molecule weight unit": {
                        "value": try_float_or_none(intermediate_structured_data["sample_data"][i].get(
                            "molecular_weight", None
                        )),
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
                sensorgram_posix_path=intermediate_structured_data["cycle_data"][i]["sensorgram_path"],
                sensorgram_posix_path_identifier=os.path.basename(
                    intermediate_structured_data["cycle_data"][i]["sensorgram_path"]
                ),
                rpoint_posix_path=intermediate_structured_data["cycle_data"][i]["r-point_path"],
                rpoint_posix_path_identifier=os.path.basename(
                    intermediate_structured_data["cycle_data"][i]["r-point_path"]
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                sample_identifier=intermediate_structured_data.get("sample_data", NOT_APPLICABLE),
                well_plate_identifier=intermediate_structured_data["application_template_details"][
                    "racks"
                ],
                method_name=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["MethodName"],
                ligand_identifier=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["Ligand"],
                flow_cell_identifier=f"Flowcell {i + 1}",
                flow_path=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["DetectionText"],
                flow_rate=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["Flow"],
                contact_time=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["ContactTime"],
                dilution=intermediate_structured_data["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["DilutePercent"],
                device_control_custom_info={
                    "number of flow cells": try_int_or_none(intermediate_structured_data["chip"].get("NoFcs", None)),
                    "number of spots": try_int_or_none(intermediate_structured_data["chip"].get("NoSpots", None)),
                    "buffer volume": {
                        "value": next(
                            value
                            for key, value in intermediate_structured_data["application_template_details"][
                                "prepare_run"
                            ].items()
                            if key.startswith("Buffer")
                        ),
                        "unit": "mL",
                    },
                },
            )
            for i in range(intermediate_structured_data["total_cycles"])
        ]


def create_measurement_groups(intermediate_structured_data: dict[str, Any]) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=intermediate_structured_data["application_template_details"]["properties"][
            "Timestamp"
        ],
        measurements= create_measurements(intermediate_structured_data),
        experiment_type=intermediate_structured_data["system_information"].get("RunTypeId", None),
        analytical_method_identifier = intermediate_structured_data["system_information"].get("TemplateFile", None),
        analyst=intermediate_structured_data["application_template_details"]["properties"].get("User", None),
        measurement_aggregate_custom_info={
            "baseline flow": {
                "value": try_float_or_none(intermediate_structured_data["application_template_details"]["BaselineFlow"].get(
                    "value", None
                ))
                if "BaselineFlow" in intermediate_structured_data["application_template_details"].keys()
                else None,
                "unit": "microlitre/min",
            },
            "data collection rate": {
                "value": try_float_or_none(intermediate_structured_data["application_template_details"]["DataCollectionRate"]
                .get("value", None))
                if "DataCollectionRate"
                in intermediate_structured_data["application_template_details"].keys()
                else None,
                "unit": "Hertz",
            }
            # "dip details": [
            #     {
            #         "datum label": "norm_dip_details",
            #         "datum value": norm_datum["response"],
            #         "sweep_row": norm_datum["sweep_row"],
            #     }
            #     for norm_datum in intermediate_structured_data["dip"]["norm_data"]
            # ]
            # + [
            #     {
            #         "datum label": "raw_dip_details",
            #         "datum value": raw_datum["response"],
            #         "sweep_row": raw_datum["sweep_row"],
            #     }
            #     for raw_datum in intermediate_structured_data["dip"]["raw_data"]
            # ],
        },
    )


