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
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.cytiva_biacore_t200 import constants
from allotropy.parsers.utils.uuids import random_uuid_str


def get_metadata(
    structure: dict[Any, Any], named_file_contents: NamedFileContents
) -> Metadata:
    if "sample_data" in structure["application_template_details"].keys():
        compartment_temperature = (
            structure.get("application_template_details", {})
            .get("RackTemperature", {})
            .get("Value", None)
        )
    else:
        compartment_temperature = structure["application_template_details"][
            "system_preparations"
        ]["RackTemp"]
    return Metadata(
        brand_name=constants.BRAND_NAME,
        device_identifier=structure["system_information"]["InstrumentId"],
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        model_number=constants.MODEL_NUMBER,
        file_name=named_file_contents.original_file_name,
        unc_path=named_file_contents.contents.name,
        software_name=structure.get("system_information", None).get(
            "Application", None
        ),
        software_version=structure.get("system_information", None).get("Version", None),
        detection_type=constants.SURFACE_PLASMON_RESONANCE,
        compartment_temperature=float(compartment_temperature)
        if compartment_temperature is not None
        else None,
        sensor_chip_type=structure["chip"].get("Name", None),
        sensor_chip_identifier=structure.get("chip", None).get("Id", None),
        device_document=[
            DeviceDocument(
                device_type=key.split()[0], device_identifier=key.split()[-1]
            )
            for key in structure["application_template_details"]
            if key.startswith("Flowcell")
        ]
        if any(
            key.startswith("Flowcell")
            for key in structure["application_template_details"]
        )
        else None,
        sensor_chip_custom_info={
            "ifc identifier": structure.get("chip", None).get("IFC", None),
            "lot number": structure.get("chip", None).get("LotNumber", None),
            "last modified_time": structure.get("chip", None).get("LastModTime", None),
            "last use time": structure.get("chip", None).get("LastUseTime", None),
            "first dock date": structure.get("chip", None).get("FirstDockDate", None),
        },
    )


def get_measurement(structure: dict[Any, Any]) -> list[Measurements]:
    if "sample_data" in structure.keys():
        detection_setting = structure["application_template_details"]["detection"]
        detection_type = detection_setting["Detection"]
        detection_key = f"Detection{detection_type}"
        detection_value = detection_setting[detection_key]
        return [
            Measurements(
                identifier=random_uuid_str(),
                sensorgram_posix_path=structure["cycle_data"][i]["sensorgram_path"],
                sensorgram_posix_path_identifier=os.path.basename(
                    structure["cycle_data"][i]["sensorgram_path"]
                ),
                rpoint_posix_path=structure["cycle_data"][i]["r-point_path"],
                rpoint_posix_path_identifier=os.path.basename(
                    structure["cycle_data"][i]["r-point_path"]
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                well_plate_identifier=structure["application_template_details"][
                    "racks"
                ],
                sample_identifier=structure["sample_data"][i].get(
                    "sample_name", NOT_APPLICABLE
                ),
                location_identifier=structure["sample_data"][i]["rack"],
                sample_role_type=structure["sample_data"][i]["role"],
                concentration=float(structure["sample_data"][i].get("concentration"))
                if "concentration" in structure["sample_data"][i].keys()
                else None,
                device_control_custom_info={
                    "number of fcs": structure.get("chip", None).get("NoFcs", None),
                    "number of spots": structure.get("chip", None).get("NoSpots", None),
                    "buffer volume": {
                        "value": next(
                            value
                            for key, value in structure["application_template_details"][
                                "prepare_run"
                            ].items()
                            if key.startswith("Buffer")
                        ),
                        "unit": "mL",
                    },
                    **{detection_key: detection_value},
                },
                sample_custom_info={
                    "molecule weight unit": {
                        "value": structure["sample_data"][i].get(
                            "molecular_weight", None
                        ),
                        "unit": "Da",
                    }
                },
            )
            for i in range(structure["total_cycles"])
        ]
    else:
        return [
            Measurements(
                identifier=random_uuid_str(),
                sensorgram_posix_path=structure["cycle_data"][i]["sensorgram_path"],
                sensorgram_posix_path_identifier=os.path.basename(
                    structure["cycle_data"][i]["sensorgram_path"]
                ),
                rpoint_posix_path=structure["cycle_data"][i]["r-point_path"],
                rpoint_posix_path_identifier=os.path.basename(
                    structure["cycle_data"][i]["r-point_path"]
                ),
                type_=MeasurementType.SURFACE_PLASMON_RESONANCE,
                device_type="binding affinity analyzer",
                sample_identifier=structure.get("sample_data", NOT_APPLICABLE),
                well_plate_identifier=structure["application_template_details"][
                    "racks"
                ],
                method_name=structure["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["MethodName"],
                ligand_identifier=structure["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["Ligand"],
                flow_cell_identifier=f"Flowcell {i + 1}",
                flow_path=structure["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["DetectionText"],
                flow_rate=structure["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["Flow"],
                contact_time=structure["application_template_details"][
                    f"Flowcell {i + 1}"
                ]["ContactTime"],
                device_control_custom_info={
                    "number of fcs": structure.get("chip", None).get("NoFcs", None),
                    "number of spots": structure.get("chip", None).get("NoSpots", None),
                    "buffer volume": {
                        "value": next(
                            value
                            for key, value in structure["application_template_details"][
                                "prepare_run"
                            ].items()
                            if key.startswith("Buffer")
                        ),
                        "unit": "mL",
                    },
                },
            )
            for i in range(structure["total_cycles"])
        ]


def get_measurement_group(structure: dict[Any, Any]) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=structure["application_template_details"]["properties"][
            "Timestamp"
        ],
        measurements=get_measurement(structure),
        experiment_type=structure.get("system_information", None).get(
            "RunTypeId", None
        ),
        analyst=structure.get("application_template_details", None)
        .get("properties", None)
        .get("Analyst", None),
        measurement_aggregate_custom_info={
            "baseline flow": {
                "value": structure["application_template_details"]["BaselineFlow"].get(
                    "value", None
                )
                if "BaselineFlow" in structure["application_template_details"].keys()
                else None,
                "unit": "microlitre/min",
            },
            "data collection rate": {
                "value": structure["application_template_details"]
                .get("DataCollectionRate", None)
                .get("value", None)
                if "DataCollectionRate"
                in structure["application_template_details"].keys()
                else None,
                "unit": "Hz",
            }
            # "dip details": [
            #     {
            #         "datum label": "norm_dip_details",
            #         "datum value": norm_datum["response"],
            #         "sweep_row": norm_datum["sweep_row"],
            #     }
            #     for norm_datum in structure["dip"]["norm_data"]
            # ]
            # + [
            #     {
            #         "datum label": "raw_dip_details",
            #         "datum value": raw_datum["response"],
            #         "sweep_row": raw_datum["sweep_row"],
            #     }
            #     for raw_datum in structure["dip"]["raw_data"]
            # ],
        },
    )


def create_data(
    structure: dict[Any, Any], named_file_contents: NamedFileContents
) -> Data:
    return Data(
        metadata=get_metadata(structure, named_file_contents),
        measurement_groups=[get_measurement_group(structure)],
        calculated_data=None,
    )
