from io import BytesIO
import re
import struct

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedDataDoc,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(handler: UnicornFileHandler) -> Metadata:
    system_data = handler.get_system_data()
    results = handler.get_results()
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
                unit="min",
            ),
        ],
        structure_measures=[data_cuve_component],
        dimensions=[
            parse_data_cube_bynary(
                data_handler.get_file_from_pattern("CoordinateData.Volumes$")
            )
        ],
        measures=[
            parse_data_cube_bynary(
                data_handler.get_file_from_pattern("CoordinateData.Amplitudes$")
            )
        ],
    )


def create_measurement_groups(handler: UnicornFileHandler) -> list[MeasurementGroup]:
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

    return [
        MeasurementGroup(
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv1_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv2_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv3_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, cond_curve, cond_component),
                    processed_data_doc=ProcessedDataDoc(
                        chromatogram_data_cube=create_data_cube(
                            handler, perc_cond_curve, perc_cond_component
                        )
                    ),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, ph_curve, ph_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
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
