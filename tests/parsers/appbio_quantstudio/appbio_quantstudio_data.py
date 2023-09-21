from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    BaselineCorrectedReporterDataCube,
    ContainerType,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ExperimentType,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    MeltingCurveDataCube,
    Model,
    NormalizedReporterDataCube,
    PassiveReferenceDyeDataCube,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    QPCRAggregateDocument,
    QPCRDocumentItem,
    ReporterDyeDataCube,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueUnitless,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Data,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    RawData,
    Result,
    Well,
    WellItem,
)


def get_data() -> Data:
    return Data(
        header=Header(
            measurement_time="2010-10-01 01:44:54 AM EDT",
            plate_well_count=96,
            barcode=None,
            device_identifier="278880034",
            model_number="QuantStudio(TM) 6 Flex System",
            device_serial_number="278880034",
            analyst=None,
            experimental_data_identifier="QuantStudio 96-Well Presence-Absence Example",
            experiment_type=ExperimentType.presence_absence_qPCR_experiment,
            measurement_method_identifier="Ct",
            qpcr_detection_chemistry="TAQMAN",
            passive_reference_dye_setting="ROX",
        ),
        wells=[
            Well(
                identifier=1,
                items={
                    "IPC": WellItem(
                        identifier=1,
                        position="A1",
                        target_dna_description="IPC",
                        sample_identifier="NAC",
                        well_location_identifier="A1",
                        reporter_dye_setting="VIC",
                        quencher_dye_setting="NFQ-MGB",
                        sample_role_type="BlockedIPC",
                        amplification_data_obj=AmplificationData(
                            total_cycle_number_setting=1,
                            cycle=[1],
                            rn=[1.064],
                            delta_rn=[-0.002],
                        ),
                        result_obj=Result(
                            cycle_threshold_value_setting=0.2,
                            cycle_threshold_result=None,
                            automatic_cycle_threshold_enabled_setting=False,
                            automatic_baseline_determination_enabled_setting=False,
                            normalized_reporter_result=1.13,
                            baseline_corrected_reporter_result=None,
                            genotyping_determination_result="Blocked IPC Control",
                            genotyping_determination_method_setting=0.0,
                        ),
                    ),
                    "TGFb": WellItem(
                        identifier=1,
                        position="A1",
                        target_dna_description="TGFb",
                        sample_identifier="NAC",
                        well_location_identifier="A1",
                        reporter_dye_setting="FAM",
                        quencher_dye_setting="NFQ-MGB",
                        sample_role_type="NTC",
                        amplification_data_obj=AmplificationData(
                            total_cycle_number_setting=1,
                            cycle=[1],
                            rn=[0.343],
                            delta_rn=[-0.007],
                        ),
                        result_obj=Result(
                            cycle_threshold_value_setting=0.2,
                            cycle_threshold_result=None,
                            automatic_cycle_threshold_enabled_setting=False,
                            automatic_baseline_determination_enabled_setting=False,
                            normalized_reporter_result=0.402,
                            baseline_corrected_reporter_result=None,
                            genotyping_determination_result="Negative Control",
                            genotyping_determination_method_setting=0.0,
                        ),
                    ),
                },
                multicomponent_data=MulticomponentData(
                    cycle=[1],
                    columns={
                        "FAM": [502840.900],
                        "ROX": [1591197.500],
                        "VIC": [1654662.500],
                    },
                ),
                melt_curve_raw_data=None,
            ),
        ],
        raw_data=RawData(
            [
                "Well\tWell Position\tCycle\tx1-m1\tx2-m2\tx3-m3\tx4-m4\tx5-m5",
                "1\t      A1\t1\t882,830.500\t1,748,809.500\t1,648,195.400\t1,513,508.200\t3,796.012",
                "",
                "",
            ]
        ),
    )


def get_data2() -> Data:
    return Data(
        header=Header(
            measurement_time="2001-12-31 09:09:19 PM EST",
            plate_well_count=384,
            barcode=None,
            device_identifier="278880086",
            model_number="ViiA 7",
            device_serial_number="278880086",
            analyst=None,
            experimental_data_identifier="200224 U251p14 200217_14v9_SEMA3F_trial 1",
            experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
            measurement_method_identifier="Ct",
            qpcr_detection_chemistry="SYBR_GREEN",
            passive_reference_dye_setting="ROX",
        ),
        wells=[
            Well(
                identifier=1,
                items={
                    "B2M-Qiagen": WellItem(
                        identifier=1,
                        position="A1",
                        target_dna_description="B2M-Qiagen",
                        sample_identifier="1. 200217 U251p14_-ab_-SEMA3F_8h_pA_1",
                        well_location_identifier="A1",
                        reporter_dye_setting="SYBR",
                        quencher_dye_setting=None,
                        sample_role_type="UNKNOWN",
                        amplification_data_obj=AmplificationData(
                            total_cycle_number_setting=1,
                            cycle=[1],
                            rn=[0.612],
                            delta_rn=[-0.007],
                        ),
                        result_obj=Result(
                            cycle_threshold_value_setting=0.277,
                            cycle_threshold_result=18.717,
                            automatic_cycle_threshold_enabled_setting=True,
                            automatic_baseline_determination_enabled_setting=True,
                            normalized_reporter_result=None,
                            baseline_corrected_reporter_result=None,
                            genotyping_determination_result=None,
                            genotyping_determination_method_setting=None,
                        ),
                    ),
                },
                multicomponent_data=MulticomponentData(
                    cycle=[1],
                    columns={
                        "ROX": [55573.94],
                        "SYBR": [34014.32],
                    },
                ),
                melt_curve_raw_data=MeltCurveRawData(
                    reading=[1],
                    fluorescence=[3.478],
                    derivative=[0.093],
                ),
            ),
        ],
        raw_data=RawData(
            [
                "Well\tWell Position\tCycle\tx1-m1\tx2-m2\tx3-m3\tx4-m4\tx5-m5",
                "1\t      A1\t1\t36,431.130\t4,790.476\t4,560.821\t56,089.960\t-387.130",
                "",
                "",
            ]
        ),
    )


def get_model() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="278880034",
                model_number="QuantStudio(TM) 6 Flex System",
                device_serial_number="278880034",
                asset_management_identifier=None,
                firmware_version=None,
                description=None,
                brand_name=None,
                product_manufacturer=None,
            ),
            qPCR_document=[
                QPCRDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        plate_well_count=TQuantityValueNumber(
                            value=96,
                            unit="#",
                            field_type=None,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2010-10-01T01:44:54-04:00",
                                target_DNA_description="IPC",
                                sample_document=SampleDocument(
                                    sample_identifier="NAC",
                                    batch_identifier=None,
                                    sample_role_type="BlockedIPC",
                                    well_location_identifier="A1",
                                    well_plate_identifier=None,
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            qPCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
                                                unit="#",
                                                field_type=None,
                                            ),
                                            denaturing_temperature_setting=None,
                                            denaturing_time_setting=None,
                                            annealing_temperature_setting=None,
                                            annealing_time_setting=None,
                                            extension_temperature_setting=None,
                                            extension_time_setting=None,
                                            reporter_dye_setting="VIC",
                                            quencher_dye_setting="NFQ-MGB",
                                            passive_reference_dye_setting="ROX",
                                        )
                                    ]
                                ),
                                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                    processed_data_document=[
                                        ProcessedDataDocumentItem(
                                            data_processing_document=DataProcessingDocument(
                                                cycle_threshold_value_setting=TQuantityValueUnitless(
                                                    value=0.2,
                                                    unit="(unitless)",
                                                    field_type=None,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=False,
                                                automatic_baseline_determination_enabled_setting=False,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=TQuantityValueUnitless(
                                                    value=0.0,
                                                    unit="(unitless)",
                                                    field_type=None,
                                                ),
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None,
                                                unit="(unitless)",
                                                field_type=None,
                                            ),
                                            normalized_reporter_result=TQuantityValueUnitless(
                                                value=1.13,
                                                unit="(unitless)",
                                                field_type=None,
                                            ),
                                            normalized_reporter_data_cube=NormalizedReporterDataCube(
                                                label="normalized reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[1.064]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            baseline_corrected_reporter_result=None,
                                            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                                                label="baseline corrected reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[-0.002]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result="Blocked IPC Control",
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=ReporterDyeDataCube(
                                    label="reporter dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[1654662.500]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                passive_reference_dye_data_cube=PassiveReferenceDyeDataCube(
                                    label="passive reference dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[1591197.500]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                melting_curve_data_cube=None,
                            ),
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2010-10-01T01:44:54-04:00",
                                target_DNA_description="TGFb",
                                sample_document=SampleDocument(
                                    sample_identifier="NAC",
                                    batch_identifier=None,
                                    sample_role_type="NTC",
                                    well_location_identifier="A1",
                                    well_plate_identifier=None,
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            qPCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
                                                unit="#",
                                                field_type=None,
                                            ),
                                            denaturing_temperature_setting=None,
                                            denaturing_time_setting=None,
                                            annealing_temperature_setting=None,
                                            annealing_time_setting=None,
                                            extension_temperature_setting=None,
                                            extension_time_setting=None,
                                            reporter_dye_setting="FAM",
                                            quencher_dye_setting="NFQ-MGB",
                                            passive_reference_dye_setting="ROX",
                                        )
                                    ]
                                ),
                                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                    processed_data_document=[
                                        ProcessedDataDocumentItem(
                                            data_processing_document=DataProcessingDocument(
                                                cycle_threshold_value_setting=TQuantityValueUnitless(
                                                    value=0.2,
                                                    unit="(unitless)",
                                                    field_type=None,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=False,
                                                automatic_baseline_determination_enabled_setting=False,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=TQuantityValueUnitless(
                                                    value=0.0,
                                                    unit="(unitless)",
                                                    field_type=None,
                                                ),
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None,
                                                unit="(unitless)",
                                                field_type=None,
                                            ),
                                            normalized_reporter_result=TQuantityValueUnitless(
                                                value=0.402,
                                                unit="(unitless)",
                                                field_type=None,
                                            ),
                                            normalized_reporter_data_cube=NormalizedReporterDataCube(
                                                label="normalized reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.343]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            baseline_corrected_reporter_result=None,
                                            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                                                label="baseline corrected reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[-0.007]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result="Negative Control",
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=ReporterDyeDataCube(
                                    label="reporter dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[502840.900]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                passive_reference_dye_data_cube=PassiveReferenceDyeDataCube(
                                    label="passive reference dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[1591197.500]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                melting_curve_data_cube=None,
                            ),
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="QuantStudio 96-Well Presence-Absence Example",
                        experiment_type=ExperimentType.presence_absence_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                        well_volume=None,
                    ),
                    analyst=None,
                    submitter=None,
                )
            ],
            data_system_document=DataSystemDocument(
                data_system_instance_identifier="localhost",
                file_name="appbio_quantstudio_test01.txt",
                UNC_path="",
                software_name="Thermo QuantStudio",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )


def get_model2() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="278880086",
                model_number="ViiA 7",
                device_serial_number="278880086",
                asset_management_identifier=None,
                firmware_version=None,
                description=None,
                brand_name=None,
                product_manufacturer=None,
            ),
            qPCR_document=[
                QPCRDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        plate_well_count=TQuantityValueNumber(
                            value=384,
                            unit="#",
                            field_type=None,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2001-12-31T21:09:19-05:00",
                                target_DNA_description="B2M-Qiagen",
                                sample_document=SampleDocument(
                                    sample_identifier="1. 200217 U251p14_-ab_-SEMA3F_8h_pA_1",
                                    batch_identifier=None,
                                    sample_role_type="UNKNOWN",
                                    well_location_identifier="A1",
                                    well_plate_identifier=None,
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            qPCR_detection_chemistry="SYBR_GREEN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
                                                unit="#",
                                                field_type=None,
                                            ),
                                            denaturing_temperature_setting=None,
                                            denaturing_time_setting=None,
                                            annealing_temperature_setting=None,
                                            annealing_time_setting=None,
                                            extension_temperature_setting=None,
                                            extension_time_setting=None,
                                            reporter_dye_setting="SYBR",
                                            quencher_dye_setting=None,
                                            passive_reference_dye_setting="ROX",
                                        )
                                    ]
                                ),
                                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                    processed_data_document=[
                                        ProcessedDataDocumentItem(
                                            data_processing_document=DataProcessingDocument(
                                                cycle_threshold_value_setting=TQuantityValueUnitless(
                                                    value=0.277,
                                                    unit="(unitless)",
                                                    field_type=None,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=None,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=18.717,
                                                unit="(unitless)",
                                                field_type=None,
                                            ),
                                            normalized_reporter_result=None,
                                            normalized_reporter_data_cube=NormalizedReporterDataCube(
                                                label="normalized reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.612]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            baseline_corrected_reporter_result=None,
                                            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                                                label="baseline corrected reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit="(unitless)",
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[-0.007]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result=None,
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=ReporterDyeDataCube(
                                    label="reporter dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[34014.32]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                passive_reference_dye_data_cube=PassiveReferenceDyeDataCube(
                                    label="passive reference dye",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.integer,
                                                concept="cycle count",
                                                unit="#",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[[55573.94]],  # type: ignore[list-item]
                                        points=None,
                                    ),
                                ),
                                melting_curve_data_cube=MeltingCurveDataCube(
                                    label="melting curve",
                                    cube_structure=TDatacubeStructure(
                                        dimensions=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="temperature",
                                                unit="degrees C",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="(unitless)",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            ),
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="slope",
                                                unit="(unitless)",
                                                scale=None,
                                                field_asm_fill_value=None,
                                            ),
                                        ],
                                    ),
                                    data=TDatacubeData(
                                        dimensions=[[1.0]],
                                        measures=[
                                            [3.478],  # type: ignore[list-item]
                                            [0.093],  # type: ignore[list-item]
                                        ],
                                        points=None,
                                    ),
                                ),
                            )
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="200224 U251p14 200217_14v9_SEMA3F_trial 1",
                        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                        well_volume=None,
                    ),
                    analyst=None,
                    submitter=None,
                )
            ],
            data_system_document=DataSystemDocument(
                data_system_instance_identifier="localhost",
                file_name="appbio_quantstudio_test02.txt",
                UNC_path="",
                software_name="Thermo QuantStudio",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )


def get_genotyping_data() -> Data:
    return Data(
        header=Header(
            measurement_time="2001-12-31T21:09:19-05:00",
            plate_well_count=96,
            barcode=None,
            device_identifier="Sponge_Bob_32",
            model_number="QuantStudio(TM) 7 Flex System",
            device_serial_number="278880032",
            analyst=None,
            experimental_data_identifier="QuantStudio 96-Well SNP Genotyping Example",
            experiment_type=ExperimentType.genotyping_qPCR_experiment,
            measurement_method_identifier="Ct",
            qpcr_detection_chemistry="TAQMAN",
            passive_reference_dye_setting="ROX",
        ),
        wells=[
            Well(
                identifier=1,
                items={
                    "CYP19_2-Allele 1": WellItem(
                        identifier=1,
                        position="A1",
                        target_dna_description="CYP19_2-Allele 1",
                        sample_identifier="NTC",
                        well_location_identifier="A1",
                        reporter_dye_setting="SYBR",
                        quencher_dye_setting=None,
                        sample_role_type="PC_ALLELE_1",
                        amplification_data_obj=AmplificationData(
                            total_cycle_number_setting=2,
                            cycle=[1, 2],
                            rn=[0.275, 0.277],
                            delta_rn=[-0.003, -0.001],
                        ),
                        result_obj=Result(
                            cycle_threshold_value_setting=0.219,
                            cycle_threshold_result=None,
                            automatic_cycle_threshold_enabled_setting=True,
                            automatic_baseline_determination_enabled_setting=True,
                            normalized_reporter_result=None,
                            baseline_corrected_reporter_result=0.016,
                            genotyping_determination_result="Negative Control (NC)",
                            genotyping_determination_method_setting=None,
                        ),
                    ),
                    "CYP19_2-Allele 2": WellItem(
                        identifier=1,
                        position="A1",
                        target_dna_description="CYP19_2-Allele 2",
                        sample_identifier="NTC",
                        well_location_identifier="A1",
                        reporter_dye_setting="SYBR",
                        quencher_dye_setting=None,
                        sample_role_type="PC_ALLELE_1",
                        amplification_data_obj=AmplificationData(
                            total_cycle_number_setting=2,
                            cycle=[1, 2],
                            rn=[0.825, 0.831],
                            delta_rn=[-0.016, -0.011],
                        ),
                        result_obj=Result(
                            cycle_threshold_value_setting=0.132,
                            cycle_threshold_result=None,
                            automatic_cycle_threshold_enabled_setting=True,
                            automatic_baseline_determination_enabled_setting=True,
                            normalized_reporter_result=None,
                            baseline_corrected_reporter_result=0.029,
                            genotyping_determination_result="Negative Control (NC)",
                            genotyping_determination_method_setting=None,
                        ),
                    ),
                },
            ),
        ],
        raw_data=None,
    )


def get_genotyping_model() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="Sponge_Bob_32",
                model_number="QuantStudio(TM) 7 Flex System",
                device_serial_number="278880032",
            ),
            qPCR_document=[
                QPCRDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        plate_well_count=TQuantityValueNumber(
                            value=96,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2001-12-31T21:09:19-05:00",
                                target_DNA_description="CYP19_2-Allele 1",
                                sample_document=SampleDocument(
                                    sample_identifier="NTC",
                                    sample_role_type="PC_ALLELE_1",
                                    well_location_identifier="A1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            qPCR_detection_chemistry="TAQMAN",
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=2.0
                                            ),
                                            reporter_dye_setting="SYBR",
                                            passive_reference_dye_setting="ROX",
                                        )
                                    ]
                                ),
                                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                    processed_data_document=[
                                        ProcessedDataDocumentItem(
                                            data_processing_document=DataProcessingDocument(
                                                cycle_threshold_value_setting=TQuantityValueUnitless(
                                                    value=0.219
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None
                                            ),
                                            normalized_reporter_data_cube=NormalizedReporterDataCube(
                                                label="normalized reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit="(unitless)",
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0, 2.0]],
                                                    measures=[[0.275, 0.277]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            baseline_corrected_reporter_result=TQuantityValueUnitless(
                                                value=0.016
                                            ),
                                            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                                                label="baseline corrected reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit="(unitless)",
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0, 2.0]],
                                                    measures=[[-0.003, -0.001]],  # type: ignore[list-item]
                                                ),
                                            ),
                                            genotyping_determination_result="Negative Control (NC)",
                                        )
                                    ]
                                ),
                            ),
                            MeasurementDocumentItem(
                                measurement_identifier="",
                                measurement_time="2001-12-31T21:09:19-05:00",
                                target_DNA_description="CYP19_2-Allele 2",
                                sample_document=SampleDocument(
                                    sample_identifier="NTC",
                                    sample_role_type="PC_ALLELE_1",
                                    well_location_identifier="A1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            qPCR_detection_chemistry="TAQMAN",
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=2.0
                                            ),
                                            reporter_dye_setting="SYBR",
                                            passive_reference_dye_setting="ROX",
                                        )
                                    ]
                                ),
                                processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                    processed_data_document=[
                                        ProcessedDataDocumentItem(
                                            data_processing_document=DataProcessingDocument(
                                                cycle_threshold_value_setting=TQuantityValueUnitless(
                                                    value=0.132
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None
                                            ),
                                            normalized_reporter_data_cube=NormalizedReporterDataCube(
                                                label="normalized reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit="(unitless)",
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0, 2.0]],
                                                    measures=[[0.825, 0.831]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            baseline_corrected_reporter_result=TQuantityValueUnitless(
                                                value=0.029
                                            ),
                                            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                                                label="baseline corrected reporter",
                                                cube_structure=TDatacubeStructure(
                                                    dimensions=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.integer,
                                                            concept="cycle count",
                                                            unit="#",
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit="(unitless)",
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0, 2.0]],
                                                    measures=[[-0.016, -0.011]],  # type: ignore[list-item]
                                                ),
                                            ),
                                            genotyping_determination_result="Negative Control (NC)",
                                        )
                                    ]
                                ),
                            ),
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="QuantStudio 96-Well SNP Genotyping Example",
                        experiment_type=ExperimentType.genotyping_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                    ),
                ),
            ],
            data_system_document=DataSystemDocument(
                data_system_instance_identifier="localhost",
                file_name="appbio_quantstudio_test03.txt",
                UNC_path="",
                software_name="Thermo QuantStudio",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )
