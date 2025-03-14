"""Maps the intermediate json to liquid chromatograhy mapper fields"""
import os
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    DeviceDocument,
    Measurement,
    MeasurementGroup,
    Metadata,
    Peak,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_openlab_cds import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
)


def create_data_cube(
    label: str,
    dimension_value: list[float],
    measures_value: list[float],
    data_cube_component: DataCubeComponent,
) -> DataCube:
    return DataCube(
        label=label,
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="retention time",
                unit="s",
            ),
        ],
        structure_measures=[data_cube_component],
        dimensions=[dimension_value],
        measures=[measures_value],
    )


def create_metadata(
    intermediate_structured_data: dict[str, Any], named_file_contents: NamedFileContents
) -> Metadata:
    return Metadata(
        asset_management_identifier=NOT_APPLICABLE,
        analyst=intermediate_structured_data["Metadata"]["Instrument"].get(
            "CreatedByUser"
        ),
        detection_type=intermediate_structured_data["Metadata"]["Instrument"].get(
            "Technique"
        ),
        model_number=intermediate_structured_data["Metadata"]["Instrument"].get("Name"),
        software_name=intermediate_structured_data["Metadata"]["Instrument"][
            "AcquisitionApplication"
        ]
        .get("AgilentApp", {})
        .get("Name"),
        file_name=os.path.basename(named_file_contents.original_file_path),
        data_system_instance_identifier=NOT_APPLICABLE,
        unc_path=named_file_contents.original_file_path,
        software_version=intermediate_structured_data["Metadata"]["Instrument"][
            "AcquisitionApplication"
        ]
        .get("AgilentApp", {})
        .get("Version"),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        brand_name=(
            intermediate_structured_data["Metadata"]["Instrument"]["Name"]
        ).split()[1]
        if intermediate_structured_data["Metadata"]["Instrument"]["Name"]
        else None,
        device_identifier=intermediate_structured_data["Metadata"]["Instrument"].get(
            "@id"
        ),
        device_documents=[
            DeviceDocument(
                device_type=assert_not_none(module.get("Type")),
                device_identifier=module.get("@id"),
                product_manufacturer=module.get("Manufacturer"),
                model_number=module.get("PartNo"),
                equipment_serial_number=module.get("SerialNo"),
                firmware_version=module.get("FirmwareRevision"),
                device_custom_info={"device name": module["Name"]}
                if module["Name"]
                else None,
            )
            for module in intermediate_structured_data["Metadata"]["Instrument"][
                "Module"
            ]
            if module["Type"] not in ["ColumnCompartment", "Detector"]
        ],
    )


def create_peak(peak_structure: list[dict[str, Any]]) -> list[Peak]:
    return [
        Peak(
            identifier=peak["@id"],
            start=float(peak["BeginTime"]["@val"]) * 60
            if "Area" in peak and peak["BeginTime"].get("@val")
            else None,
            end=float(peak["EndTime"]["@val"]) * 60
            if "Area" in peak and peak["EndTime"].get("@val")
            else None,
            start_unit="s",
            end_unit="s",
            area=try_float_or_none(peak["Area"]["@val"]),
            area_unit="RFU.s"
            if "LU" in peak["Area"]["@unit"]
            else "mAU.s"
            if "Area" in peak and peak["Area"].get("@unit")
            else None,
            height=try_float_or_none(peak.get("Height", {}).get("@val"))
            if try_float_or_none(peak.get("Height", {}).get("@val")) is not None
            else None,
            height_unit="RFU"
            if "LU" in peak["Height"]["@unit"]
            else "mAU"
            if "Height" in peak and peak["Height"].get("@unit")
            else None,
            written_name=peak["Peak Metadata"].get("CompoundName"),
            retention_time=float(peak["RetentionTime"]["@val"]) * 60
            if peak.get("RetentionTime")
            and peak["RetentionTime"].get("@val") is not None
            else None,
            chromatographic_resolution=try_float_or_none(
                peak.get("Resolution_USP", {}).get("@val")
            ),
            width_at_half_height=float(peak.get("Width_50Perc", {}).get("@val")) * 60
            if peak.get("Width_50Perc") and peak["Width_50Perc"].get("@val") is not None
            else None,
            asymmetry_factor_measured_at_10_percent_height=try_float_or_none(
                peak.get("Width_50Perc", {}).get("@val")
            ),
            width_at_half_height_unit="s",
            peak_width_at_5_percent_of_height=float(
                peak.get("Width_5Perc", {}).get("@val")
            )
            * 60
            if peak.get("Width_5Perc") and peak["Width_5Perc"].get("@val") is not None
            else None,
            peak_width_at_10_percent_of_height=float(
                peak.get("Width_10Perc", {}).get("@val")
            )
            * 60
            if peak.get("Width_10Perc") and peak["Width_10Perc"].get("@val") is not None
            else None,
            peak_width_at_baseline=float(peak.get("WidthBase", {}).get("@val")) * 60
            if peak.get("WidthBase") and peak["WidthBase"].get("@val") is not None
            else None,
            number_of_theoretical_plates__chromatography_=try_float_or_none(
                peak.get("TheoreticalPlates_USP", {}).get("@val")
            ),
        )
        for peak in peak_structure
    ]


def create_measurements(
    intermediate_structured_data: dict[str, Any]
) -> list[Measurement]:
    column_comp_dict = next(
        (
            module
            for module in intermediate_structured_data["Metadata"]["Instrument"][
                "Module"
            ]
            if module["Name"] == "Column Comp."
        ),
        None,
    )
    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            processed_data_identifier=random_uuid_str(),
            measurement_time=intermediate_structured_data["Metadata"]["Instrument"].get(
                "CreationDate"
            ),
            sample_identifier=intermediate_structured_data["Result Data"][i][
                "Sample Data"
            ].get("SampleName"),
            sample_role_type=constants.SAMPLE_ROLE_TYPE.get(
                intermediate_structured_data["Result Data"][i]["Sample Data"][
                    "SampleSetup"
                ]
                .get("DAParam", {})
                .get("Type")
            ),
            sample_custom_info={
                "location identifier": intermediate_structured_data["Result Data"][i][
                    "Sample Data"
                ].get("Location"),
                "replicate": intermediate_structured_data["Result Data"][i][
                    "Sample Data"
                ].get("Replicate"),
                "sample amount": {
                    "value": try_float_or_none(
                        intermediate_structured_data["Result Data"][i]["Sample Data"][
                            "SampleSetup"
                        ]
                        .get("DAParam", {})
                        .get("SampleAmount", {})
                        .get("@val")
                    ),
                    "unit": intermediate_structured_data["Result Data"][i][
                        "Sample Data"
                    ]["SampleSetup"]["DAParam"]["SampleAmount"]["@unit"]
                    or "(unitless)",
                }
                if "SampleAmount"
                in intermediate_structured_data["Result Data"][i]["Sample Data"][
                    "SampleSetup"
                ]["DAParam"]
                else None,
                "barcode": intermediate_structured_data["Result Data"][i][
                    "Sample Data"
                ].get("Barcode"),
            },
            injection_identifier=assert_not_none(
                (
                    intermediate_structured_data["Result Data"][i]["Sample Data"][
                        "SampleMeasurement"
                    ]
                    .get("InjectionMeasData_ID", {})
                    .get("@id")
                )
                if isinstance(
                    intermediate_structured_data["Result Data"][i]["Sample Data"][
                        "SampleMeasurement"
                    ]["InjectionMeasData_ID"],
                    dict,
                )
                else (
                    intermediate_structured_data["Result Data"][i]["Sample Data"][
                        "SampleMeasurement"
                    ]["InjectionMeasData_ID"][
                        int(
                            intermediate_structured_data["Result Data"][i][
                                "Sample Data"
                            ]["Replicate"]
                        )
                        - 1
                    ].get(
                        "@id"
                    )
                )
            ),
            injection_time=assert_not_none(
                intermediate_structured_data["Result Data"][i]["Sample Data"].get(
                    "RunDateTime"
                )
            ),
            autosampler_injection_volume_setting=assert_not_none(
                float(
                    intermediate_structured_data["Result Data"][i]["Sample Data"].get(
                        "InjectionVolume"
                    )
                )
            ),
            injection_custom_info={
                "injection source": intermediate_structured_data["Result Data"][i][
                    "Sample Data"
                ].get("InjectionSource"),
                "acquisition method identifier": intermediate_structured_data[
                    "Result Data"
                ][i]["Sample Data"].get("AcquisitionMethod"),
                "injector position": intermediate_structured_data["Result Data"][i][
                    "Sample Data"
                ]["SampleSetup"]
                .get("AcqParam", {})
                .get("InjectorPosition"),
            },
            chromatography_serial_num=column_comp_dict.get("SerialNo")
            if column_comp_dict
            else None,
            chromatography_part_num=column_comp_dict.get("PartNo")
            if column_comp_dict
            else None,
            column_inner_diameter=try_float_or_none(
                intermediate_structured_data["Metadata"]["SeparationMedium"][0]["Type"][
                    "Column"
                ]
                .get("Diameter", {})
                .get("@val")
            ),
            chromatography_particle_size=try_float_or_none(
                intermediate_structured_data["Metadata"]["SeparationMedium"][0]["Type"][
                    "Column"
                ]
                .get("ParticleSize", {})
                .get("@val")
            ),
            chromatography_length=float(
                intermediate_structured_data["Metadata"]["SeparationMedium"][0]["Type"][
                    "Column"
                ]["Length"]["@val"]
            )
            / 10
            if "Length"
            in intermediate_structured_data["Metadata"]["SeparationMedium"][0]["Type"][
                "Column"
            ]
            else None,
            column_product_manufacturer=column_comp_dict.get("Manufacturer")
            if column_comp_dict
            else None,
            column_custom_info={
                "maximum temperature": {
                    "value": try_float_or_none(
                        intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                            "Type"
                        ]["Column"]["MaxTemp"]["@val"]
                    ),
                    "unit": "degC"
                    if intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                        "Type"
                    ]["Column"]["MaxTemp"]["@unit"]
                    == "°C"
                    else (
                        intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                            "Type"
                        ]["Column"]["MaxTemp"]["@unit"]
                        or "(unitless)"
                    ),
                }
                if "MaxTemp"
                in intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                    "Type"
                ]["Column"]
                else None,
                "maximum pressure": {
                    "value": try_float_or_none(
                        intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                            "Type"
                        ]["Column"]["MaxPressure"]["@val"]
                    ),
                    "unit": intermediate_structured_data["Metadata"][
                        "SeparationMedium"
                    ][0]["Type"]["Column"]["MaxPressure"]["@unit"]
                    or "(unitless)",
                }
                if "MaxPressure"
                in intermediate_structured_data["Metadata"]["SeparationMedium"][0][
                    "Type"
                ]["Column"]
                else None,
                "firmware version": column_comp_dict.get("FirmwareRevision")
                if column_comp_dict
                else None,
            },
            device_control_docs=[
                DeviceControlDoc(
                    device_type="pump",
                    system_pressure_data_cube=create_data_cube(
                        label="pump pressure",
                        measures_value=intermediate_structured_data["Result Data"][i][
                            "Pressure"
                        ],
                        dimension_value=intermediate_structured_data["Result Data"][i][
                            "Time"
                        ],
                        data_cube_component=DataCubeComponent(
                            type_=FieldComponentDatatype.double,
                            concept="pump pressure",
                            unit="MPa",
                        ),
                    ),
                )
            ]
            if "Pressure"
            in intermediate_structured_data["Result Data"][i]["Metadata"]["signal"]
            else [
                DeviceControlDoc(
                    device_type=assert_not_none(module.get("Name")),
                    detection_type="Fluorescence"
                    if module.get("Name") == "FLD"
                    else "Absorbance",
                    device_identifier=module.get("@id"),
                    product_manufacturer=module.get("Manufacturer"),
                    model_number=module.get("PartNo"),
                    equipment_serial_number=module.get("SerialNo"),
                    firmware_version=module.get("FirmwareRevision"),
                    excitation_wavelength_setting=try_float_or_none(
                        intermediate_structured_data["Result Data"][i]["Metadata"][
                            "signal"
                        ]
                        .split("Ex=")[1]
                        .split(",")[0]
                    )
                    if module["Name"] == "FLD"
                    and "FLD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else None,
                    detector_bandwidth_setting=try_float_or_none(
                        intermediate_structured_data["Result Data"][i]["Metadata"][
                            "signal"
                        ]
                        .split(",")[2]
                        .split()[0]
                    )
                    if module["Name"] == "DAD"
                    and "DAD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else None,
                    detector_wavelength_setting=try_float_or_none(
                        intermediate_structured_data["Result Data"][i]["Metadata"][
                            "signal"
                        ]
                        .split("Sig=")[1]
                        .split(",")[0]
                    )
                    if "DAD" in module["Name"]
                    and "DAD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else try_float_or_none(
                        intermediate_structured_data["Result Data"][i]["Metadata"][
                            "signal"
                        ]
                        .split("Em=")[1]
                        .strip()
                    )
                    if module["Name"] == "FLD"
                    and "FLD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else None,
                )
                for module in intermediate_structured_data["Metadata"]["Instrument"][
                    "Module"
                ]
                if (
                    "DAD" in module["Name"]
                    and "DAD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                )
                or (
                    "FLD" in module["Name"]
                    and "FLD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                )
            ],
            peaks=create_peak(intermediate_structured_data["Result Data"][i]["Peak"])
            if "Peak" in intermediate_structured_data["Result Data"][i]
            else None,
            chromatogram_data_cube=create_data_cube(
                label=f"{intermediate_structured_data['Result Data'][i]['Metadata']['signal'].split(',')[0]} chromatogram",
                measures_value=intermediate_structured_data["Result Data"][i][
                    "Intensity"
                ],
                dimension_value=intermediate_structured_data["Result Data"][i]["Time"],
                data_cube_component=DataCubeComponent(
                    type_=FieldComponentDatatype.double,
                    concept="absorbance"
                    if "DAD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else "fluorescence",
                    unit="mAU"
                    if "DAD"
                    in intermediate_structured_data["Result Data"][i]["Metadata"][
                        "signal"
                    ]
                    else "RFU",
                ),
            )
            if "PMP"
            not in intermediate_structured_data["Result Data"][i]["Metadata"]["signal"]
            else None,
        )
        for i in range(intermediate_structured_data["Sample Count"]["count"])
    ]


def create_measurement_groups(
    intermediate_structured_data: dict[str, Any]
) -> MeasurementGroup:
    return MeasurementGroup(
        measurements=create_measurements(intermediate_structured_data),
        measurement_aggregate_custom_info={
            "analytical method identifier": intermediate_structured_data["Result Data"][
                0
            ]["Sample Data"].get("AnalysisMethod")
        },
    )
