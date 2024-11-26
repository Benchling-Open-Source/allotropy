from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCubeComponent,
    DeviceControlDoc,
    Measurement,
    MeasurementGroup,
    ProcessedDataDoc,
)
from allotropy.parsers.cytiva_unicorn.constants import DEVICE_TYPE
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
)
from allotropy.parsers.cytiva_unicorn.structure.measurement import (
    UnicornMeasurement,
)
from allotropy.parsers.cytiva_unicorn.structure.static_docs import (
    StaticDocs,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement_groups(
    handler: UnicornFileHandler, results: StrictElement
) -> list[MeasurementGroup]:
    chrom_1 = handler.get_chrom_1()
    curves = chrom_1.find("Curves")
    elements = curves.findall("Curve")

    static_docs = StaticDocs.create(handler, curves.find("Curve"), results)

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

    uv1_curve = handler.filter_curve(elements, r"^UV 1_\d+$")
    uv2_curve = handler.filter_curve(elements, r"^UV 2_\d+$")
    uv3_curve = handler.filter_curve(elements, r"^UV 3_\d+$")
    cond_curve = handler.filter_curve(elements, r"^Cond$")
    perc_cond_curve = handler.filter_curve(elements, r"^% Cond$")
    ph_curve = handler.filter_curve(elements, r"^pH$")
    conc_b_curve = handler.filter_curve(elements, r"^Conc B$")
    derived_pressure_curve = handler.filter_curve(elements, r"^DeltaC pressure$")
    pre_column_pressure_data_cube = handler.filter_curve(elements, r"^PreC pressure$")
    sample_pressure_data_cube = handler.filter_curve(elements, r"^Sample pressure$")
    system_pressure_data_cube = handler.filter_curve(elements, r"^System pressure$")
    post_column_pressure_data_cube = handler.filter_curve(elements, r"^PostC pressure$")
    sample_flow_cv_data_cube = handler.filter_curve(elements, r"^Sample flow \(CV/h\)$")
    system_flow_cv_data_cube = handler.filter_curve(elements, r"^System flow \(CV/h\)$")
    sample_flow_data_cube = handler.filter_curve(elements, r"^Sample flow$")
    system_flow_data_cube = handler.filter_curve(elements, r"^System flow$")
    sample_linear_flow_data_cube = handler.filter_curve(
        elements, r"^Sample linear flow$"
    )
    temperature_profile_data_cube = handler.filter_curve(elements, r"^Cond temp$")

    return [
        MeasurementGroup(
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    chromatogram_data_cube=UnicornMeasurement.create_data_cube(
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
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    chromatogram_data_cube=UnicornMeasurement.create_data_cube(
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
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    chromatogram_data_cube=UnicornMeasurement.create_data_cube(
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
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    chromatogram_data_cube=UnicornMeasurement.create_data_cube(
                        handler, cond_curve, cond_component
                    ),
                    processed_data_doc=ProcessedDataDoc(
                        chromatogram_data_cube=UnicornMeasurement.create_data_cube(
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
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    chromatogram_data_cube=UnicornMeasurement.create_data_cube(
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
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            solvent_conc_data_cube=UnicornMeasurement.create_data_cube(
                                handler, conc_b_curve, conc_b_component
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    processed_data_doc=ProcessedDataDoc(
                        derived_column_pressure_data_cube=UnicornMeasurement.create_data_cube(
                            handler, derived_pressure_curve, derived_pressure_component
                        )
                    ),
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            pre_column_pressure_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                pre_column_pressure_data_cube,
                                pre_column_pressure_component,
                            ),
                            sample_pressure_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                sample_pressure_data_cube,
                                sample_pressure_component,
                            ),
                            system_pressure_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                system_pressure_data_cube,
                                system_pressure_component,
                            ),
                            post_column_pressure_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                post_column_pressure_data_cube,
                                post_column_pressure_component,
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                sample_flow_cv_data_cube,
                                sample_flow_cv_component,
                            ),
                            system_flow_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                system_flow_cv_data_cube,
                                system_flow_cv_component,
                            ),
                        ),
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                                handler, sample_flow_data_cube, sample_flow_component
                            ),
                            system_flow_data_cube=UnicornMeasurement.create_data_cube(
                                handler, system_flow_data_cube, system_flow_component
                            ),
                        ),
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            sample_flow_data_cube=UnicornMeasurement.create_data_cube(
                                handler,
                                sample_linear_flow_data_cube,
                                sample_linear_flow_component,
                            ),
                        ),
                    ],
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    chromatography_column_doc=static_docs.chromatography_doc,
                    injection_doc=static_docs.injection_doc,
                    sample_doc=static_docs.sample_doc,
                    device_control_docs=[
                        DeviceControlDoc(
                            device_type=DEVICE_TYPE,
                            temperature_profile_data_cube=UnicornMeasurement.create_data_cube(
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
