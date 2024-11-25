from io import BytesIO
import re
import struct

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatographyDoc,
    DataCube,
    DataCubeComponent,
    DeviceControlDoc,
    InjectionDoc,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedDataDoc,
    SampleDoc,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float


def create_metadata(handler: UnicornFileHandler, results: StrictElement) -> Metadata:
    system_data = handler.get_system_data()
    instrument_config_data = handler.get_instrument_config_data()

    return Metadata(
        asset_management_id=system_data.find_attr(
            ["System", "InstrumentConfiguration"], "Description"
        ),
        product_manufacturer="Cytiva Life Sciences",
        device_id=results.find_text(["SystemName"]),
        firmware_version=instrument_config_data.find_text(["FirmwareVersion"]),
        analyst=handler.get_audit_trail_entry_user(),
    )


def filter_curve(curve_elements: list[StrictElement], pattern: str) -> StrictElement:
    for element in curve_elements:
        if re.search(pattern, element.find_text(["Name"])):
            return element
    msg = f"Unable to find curve element with pattern {pattern}"
    raise AllotropeConversionError(msg)


def parse_data_cube_bynary(stream: BytesIO) -> tuple[float, ...]:
    data = stream.read()
    # assuming little endian float (4 bytes)
    return tuple(
        struct.unpack("<f", data[i : i + 4])[0] for i in range(47, len(data) - 48, 4)
    )


def min_to_sec(data: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(element * 60 for element in data)


def create_data_cube(
    handler: UnicornFileHandler,
    curve_element: StrictElement,
    data_cuve_component: DataCubeComponent,
) -> DataCube:
    data_name = curve_element.find_text(
        ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
    )
    data_handler = handler.get_content_from_pattern(data_name)

    return DataCube(
        label=curve_element.find_text(["Name"]),
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="s",
            ),
        ],
        structure_measures=[data_cuve_component],
        dimensions=[
            min_to_sec(
                parse_data_cube_bynary(
                    data_handler.get_file_from_pattern("CoordinateData.Volumes$")
                )
            )
        ],
        measures=[
            parse_data_cube_bynary(
                data_handler.get_file_from_pattern("CoordinateData.Amplitudes$")
            )
        ],
    )


def get_chromatography_doc(handler: UnicornFileHandler) -> ChromatographyDoc:
    column_type_data = handler.get_column_type_data()
    return ChromatographyDoc(
        chromatography_serial_num=column_type_data.find_text(
            ["ColumnType", "Hardware", "ArticleNumber"]
        ),
        column_inner_diameter=try_float(
            column_type_data.find_text(["ColumnType", "Hardware", "Diameter"]),
            "column inner diameter",
        ),
        chromatography_chemistry_type=column_type_data.find_text(
            ["ColumnType", "Media", "TechniqueName"]
        ),
        chromatography_particle_size=try_float(
            column_type_data.find_text(
                ["ColumnType", "Media", "AverageParticleDiameter"]
            ),
            "chromatography particle size",
        ),
    )


def filter_result_criteria(results: StrictElement, keyword: str) -> StrictElement:
    for result_criteria in results.find("ResultSearchCriterias").findall(
        "ResultSearchCriteria"
    ):
        if result_criteria.find_text(["Keyword1"]) == keyword:
            return result_criteria
    msg = f"Unable to find result criteria with keyword 1 '{keyword}'"
    raise AllotropeConversionError(msg)


def get_injection_doc(
    curve_element: StrictElement, results: StrictElement
) -> InjectionDoc:
    result = filter_result_criteria(results, keyword="Sample volume")
    return InjectionDoc(
        injection_identifier=random_uuid_str(),
        injection_time=curve_element.find_text(["MethodStartTime"]),
        autosampler_injection_volume_setting=try_float(
            result.find_text(["Keyword2"]),
            "autosampler injection volume setting",
        ),
    )


def get_sample_doc(results: StrictElement) -> SampleDoc:
    result = filter_result_criteria(results, keyword="Sample_ID")
    return SampleDoc(
        sample_identifier=result.find_text(["Keyword2"]),
        batch_identifier=results.find_text(["BatchId"]),
    )


def create_measurement_groups(
    handler: UnicornFileHandler, results: StrictElement
) -> list[MeasurementGroup]:
    chrom_1 = handler.get_chrom_1()
    elements = chrom_1.find("Curves").findall("Curve")

    uv_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="absorbance",
        unit="mAU",
    )

    cond_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="electric conductivity",
        unit="S/m",
    )

    perc_cond_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="electric conductivity",
        unit="%",
    )

    ph_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="pH",
        unit="pH",
    )

    conc_b_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="solvent concentration",
        unit="%",
    )

    derived_pressure_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="delta column pressure",
        unit="MPa",
    )

    pre_column_pressure_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="pre-column pressure",
        unit="MPa",
    )

    sample_pressure_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="sample pressure",
        unit="MPa",
    )

    system_pressure_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="system pressure",
        unit="MPa",
    )

    post_column_pressure_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="post-column pressure",
        unit="MPa",
    )

    sample_flow_cv_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="sample flow",
        unit="CV/h",
    )

    system_flow_cv_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="system flow",
        unit="CV/h",
    )

    sample_flow_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="sample flow",
        unit="mL/min",
    )

    system_flow_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="system flow",
        unit="mL/min",
    )

    sample_linear_flow_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="sample flow",
        unit="cm/s",
    )

    temperature_profile_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="temperature",
        unit="degC",
    )

    uv1_curve = filter_curve(elements, r"^UV 1_\d+$")
    uv2_curve = filter_curve(elements, r"^UV 2_\d+$")
    uv3_curve = filter_curve(elements, r"^UV 3_\d+$")
    cond_curve = filter_curve(elements, r"^Cond$")
    perc_cond_curve = filter_curve(elements, r"^% Cond$")
    ph_curve = filter_curve(elements, r"^pH$")
    conc_b_curve = filter_curve(elements, r"^Conc B$")
    derived_pressure_curve = filter_curve(elements, r"^DeltaC pressure$")
    pre_column_pressure_data_cube = filter_curve(elements, r"^PreC pressure$")
    sample_pressure_data_cube = filter_curve(elements, r"^Sample pressure$")
    system_pressure_data_cube = filter_curve(elements, r"^System pressure$")
    post_column_pressure_data_cube = filter_curve(elements, r"^PostC pressure$")
    sample_flow_cv_data_cube = filter_curve(elements, r"^Sample flow \(CV/h\)$")
    system_flow_cv_data_cube = filter_curve(elements, r"^System flow \(CV/h\)$")
    sample_flow_data_cube = filter_curve(elements, r"^Sample flow$")
    system_flow_data_cube = filter_curve(elements, r"^System flow$")
    sample_linear_flow_data_cube = filter_curve(elements, r"^Sample linear flow$")
    temperature_profile_data_cube = filter_curve(elements, r"^Cond temp$")

    chromatography_doc = get_chromatography_doc(handler)
    injection_doc = get_injection_doc(uv1_curve, results)
    sample_doc = get_sample_doc(results)

    return [
        MeasurementGroup(
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    chromatogram_data_cube=create_data_cube(
                        handler, uv1_curve, uv_component
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                        )
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    chromatogram_data_cube=create_data_cube(
                        handler, uv2_curve, uv_component
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                        )
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    chromatogram_data_cube=create_data_cube(
                        handler, uv3_curve, uv_component
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                        )
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    chromatogram_data_cube=create_data_cube(
                        handler, cond_curve, cond_component
                    ),
                    processed_data_doc=ProcessedDataDoc(
                        chromatogram_data_cube=create_data_cube(
                            handler, perc_cond_curve, perc_cond_component
                        )
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                        )
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    chromatogram_data_cube=create_data_cube(
                        handler, ph_curve, ph_component
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                        )
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            solvent_conc_data_cube=create_data_cube(
                                handler, conc_b_curve, conc_b_component
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    processed_data_doc=ProcessedDataDoc(
                        derived_column_pressure_data_cube=create_data_cube(
                            handler, derived_pressure_curve, derived_pressure_component
                        )
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            pre_column_pressure_data_cube=create_data_cube(
                                handler,
                                pre_column_pressure_data_cube,
                                pre_column_pressure_component,
                            ),
                            sample_pressure_data_cube=create_data_cube(
                                handler,
                                sample_pressure_data_cube,
                                sample_pressure_component,
                            ),
                            system_pressure_data_cube=create_data_cube(
                                handler,
                                system_pressure_data_cube,
                                system_pressure_component,
                            ),
                            post_column_pressure_data_cube=create_data_cube(
                                handler,
                                post_column_pressure_data_cube,
                                post_column_pressure_component,
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=create_data_cube(
                                handler,
                                sample_flow_cv_data_cube,
                                sample_flow_cv_component,
                            ),
                            system_flow_data_cube=create_data_cube(
                                handler,
                                system_flow_cv_data_cube,
                                system_flow_cv_component,
                            ),
                        ),
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=create_data_cube(
                                handler, sample_flow_data_cube, sample_flow_component
                            ),
                            system_flow_data_cube=create_data_cube(
                                handler, system_flow_data_cube, system_flow_component
                            ),
                        ),
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=create_data_cube(
                                handler,
                                sample_linear_flow_data_cube,
                                sample_linear_flow_component,
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=chromatography_doc,
                    injection_doc=injection_doc,
                    sample_doc=sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            temperature_profile_data_cube=create_data_cube(
                                handler,
                                temperature_profile_data_cube,
                                temperature_profile_component,
                            ),
                        ),
                    ],
                ),
            ]
        )
    ]
