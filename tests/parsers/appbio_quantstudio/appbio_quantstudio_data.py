from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    BaselineCorrectedReporterDataCube,
    CalculatedDataDocumentItem,
    ContainerType,
    DataProcessingDocument,
    DataProcessingDocument1,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
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
    TCalculatedDataAggregateDocument,
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
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import Data
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    _create_data,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    Result,
    ResultMetadata,
    Well,
    WellItem,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)

ASM_CONVERTER_NAME = "allotropy_appbio_quantstudio_rt_pcr"


def get_data(file_name: str) -> Data:
    well_id = 1
    well_item_id = 1
    target1 = "IPC"
    target2 = "TGFb"
    header = Header(
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
        pcr_detection_chemistry="TAQMAN",
        passive_reference_dye_setting="ROX",
    )
    amp_data = {
        well_item_id: {
            target1: AmplificationData(
                total_cycle_number_setting=1,
                cycle=[1],
                rn=[1.064],
                delta_rn=[-0.002],
            ),
            target2: AmplificationData(
                total_cycle_number_setting=1,
                cycle=[1],
                rn=[0.343],
                delta_rn=[-0.007],
            ),
        }
    }
    result_data = {
        well_item_id: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.2,
                cycle_threshold_result=None,
                automatic_cycle_threshold_enabled_setting=False,
                automatic_baseline_determination_enabled_setting=False,
                normalized_reporter_result=1.13,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result="Blocked IPC Control",
                genotyping_determination_method_setting=0.0,
                quantity=None,
                quantity_mean=None,
                quantity_sd=None,
                ct_mean=None,
                ct_sd=None,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=None,
                rq_min=None,
                rq_max=None,
                rn_mean=1.261,
                rn_sd=0.088,
                y_intercept=None,
                r_squared=None,
                slope=None,
                efficiency=None,
            ),
            target2.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.2,
                cycle_threshold_result=None,
                automatic_cycle_threshold_enabled_setting=False,
                automatic_baseline_determination_enabled_setting=False,
                normalized_reporter_result=0.402,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result="Negative Control",
                genotyping_determination_method_setting=0.0,
                quantity=None,
                quantity_mean=None,
                quantity_sd=None,
                ct_mean=None,
                ct_sd=None,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=None,
                rq_min=None,
                rq_max=None,
                rn_mean=0.397,
                rn_sd=0.006,
                y_intercept=None,
                r_squared=None,
                slope=None,
                efficiency=None,
            ),
        }
    }
    result_metadata = ResultMetadata(
        reference_dna_description=None,
        reference_sample_description=None,
    )
    multi_data = {
        well_id: MulticomponentData(
            cycle=[1],
            columns={
                "FAM": [502840.900],
                "ROX": [1591197.500],
                "VIC": [1654662.500],
            },
        )
    }
    well = Well(
        identifier=well_id,
        items=[
            WellItem(
                uuid="d170f2df-7ff8-4978-b13d-a7ad19fab824",
                identifier=well_item_id,
                position="A1",
                target_dna_description=target1,
                sample_identifier="NAC",
                well_location_identifier="A1",
                reporter_dye_setting="VIC",
                quencher_dye_setting="NFQ-MGB",
                sample_role_type="BlockedIPC",
            ),
            WellItem(
                uuid="ba281c64-0605-4e76-8e9c-2a183be3cc08",
                identifier=well_item_id,
                position="A1",
                target_dna_description=target2,
                sample_identifier="NAC",
                well_location_identifier="A1",
                reporter_dye_setting="FAM",
                quencher_dye_setting="NFQ-MGB",
                sample_role_type="NTC",
            ),
        ],
    )
    calculated_documents = [
        CalculatedDocument(
            uuid="d006e7e7-fbe4-47cf-821b-904e85202803",
            name="rn mean",
            value=1.261,
            iterated=True,
            data_sources=[
                DataSource(
                    feature="normalized reporter result",
                    reference=well.items[0],
                ),
            ],
        ),
        CalculatedDocument(
            uuid="f4fee39c-5861-4203-afcf-94ee755ac0b4",
            name="rn sd",
            value=0.088,
            iterated=True,
            data_sources=[
                DataSource(
                    feature="normalized reporter result",
                    reference=well.items[0],
                ),
            ],
        ),
        CalculatedDocument(
            uuid="e6707b0c-4494-412f-8a8e-ef51d01f25b3",
            name="rn mean",
            value=0.397,
            iterated=True,
            data_sources=[
                DataSource(
                    feature="normalized reporter result",
                    reference=well.items[1],
                ),
            ],
        ),
        CalculatedDocument(
            uuid="da78a225-2c34-40b3-b487-97893bfe491a",
            name="rn sd",
            value=0.006,
            iterated=True,
            data_sources=[
                DataSource(
                    feature="normalized reporter result",
                    reference=well.items[1],
                ),
            ],
        ),
    ]
    return _create_data(
        file_name,
        header,
        wells=[well],
        amp_data=amp_data,
        multi_data=multi_data,
        results_data=result_data,
        results_metadata=result_metadata,
        melt_data={},
        calculated_documents=calculated_documents,
    )


def get_data2(file_name: str) -> Data:
    well_id = 1
    well_item_id = 1
    target1 = "B2M-Qiagen"
    header = Header(
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
        pcr_detection_chemistry="SYBR_GREEN",
        passive_reference_dye_setting="ROX",
    )
    amp_data = {
        well_item_id: {
            target1: AmplificationData(
                total_cycle_number_setting=1,
                cycle=[1],
                rn=[0.612],
                delta_rn=[-0.007],
            ),
        }
    }
    result_data = {
        well_item_id: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.277,
                cycle_threshold_result=18.717,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
                quantity=None,
                quantity_mean=None,
                quantity_sd=None,
                ct_mean=18.717,
                ct_sd=None,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=None,
                rq_min=None,
                rq_max=None,
                rn_mean=None,
                rn_sd=None,
                y_intercept=None,
                r_squared=None,
                slope=None,
                efficiency=None,
            )
        }
    }
    result_metadata = ResultMetadata(
        reference_dna_description=NOT_APPLICABLE,
        reference_sample_description=NOT_APPLICABLE,
    )
    multi_data = {
        well_id: MulticomponentData(
            cycle=[1],
            columns={
                "ROX": [55573.94],
                "SYBR": [34014.32],
            },
        )
    }
    melt_data = {
        well_id: MeltCurveRawData(
            reading=[1],
            fluorescence=[3.478],
            derivative=[0.093],
        )
    }
    well = Well(
        identifier=well_id,
        items=[
            WellItem(
                uuid="1e572828d-45fd-49bd-ab66-2a7f06aea3b6",
                identifier=well_item_id,
                position="A1",
                target_dna_description=target1,
                sample_identifier="1. 200217 U251p14_-ab_-SEMA3F_8h_pA_1",
                well_location_identifier="A1",
                reporter_dye_setting="SYBR",
                quencher_dye_setting=None,
                sample_role_type="UNKNOWN",
            )
        ],
    )

    return _create_data(
        file_name,
        header,
        wells=[well],
        amp_data=amp_data,
        multi_data=multi_data,
        results_data=result_data,
        results_metadata=result_metadata,
        melt_data=melt_data,
        calculated_documents=[],
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
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="d170f2df-7ff8-4978-b13d-a7ad19fab824",
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
                                            PCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
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
                                                ),
                                                automatic_cycle_threshold_enabled_setting=False,
                                                automatic_baseline_determination_enabled_setting=False,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=TQuantityValueUnitless(
                                                    value=0.0,
                                                ),
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None,
                                            ),
                                            normalized_reporter_result=TQuantityValueUnitless(
                                                value=1.13,
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
                                                            unit=UNITLESS,
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit=UNITLESS,
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
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
                                measurement_identifier="ba281c64-0605-4e76-8e9c-2a183be3cc08",
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
                                            PCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
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
                                                ),
                                                automatic_cycle_threshold_enabled_setting=False,
                                                automatic_baseline_determination_enabled_setting=False,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=TQuantityValueUnitless(
                                                    value=0.0,
                                                ),
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=None,
                                            ),
                                            normalized_reporter_result=TQuantityValueUnitless(
                                                value=0.402,
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
                                                            unit=UNITLESS,
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit=UNITLESS,
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
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
            calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                calculated_data_document=[
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="d006e7e7-fbe4-47cf-821b-904e85202803",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="d170f2df-7ff8-4978-b13d-a7ad19fab824",
                                    data_source_feature="normalized reporter result",
                                )
                            ]
                        ),
                        data_processing_document=None,
                        calculated_data_name="rn mean",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=1.261, unit=UNITLESS
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="f4fee39c-5861-4203-afcf-94ee755ac0b4",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="d170f2df-7ff8-4978-b13d-a7ad19fab824",
                                    data_source_feature="normalized reporter result",
                                )
                            ]
                        ),
                        data_processing_document=None,
                        calculated_data_name="rn sd",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.088, unit=UNITLESS
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="e6707b0c-4494-412f-8a8e-ef51d01f25b3",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="ba281c64-0605-4e76-8e9c-2a183be3cc08",
                                    data_source_feature="normalized reporter result",
                                )
                            ]
                        ),
                        data_processing_document=None,
                        calculated_data_name="rn mean",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.397, unit=UNITLESS
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="da78a225-2c34-40b3-b487-97893bfe491a",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="ba281c64-0605-4e76-8e9c-2a183be3cc08",
                                    data_source_feature="normalized reporter result",
                                )
                            ]
                        ),
                        data_processing_document=None,
                        calculated_data_name="rn sd",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.006, unit=UNITLESS
                        ),
                    ),
                ]
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
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="1e572828d-45fd-49bd-ab66-2a7f06aea3b6",
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
                                            PCR_detection_chemistry="SYBR_GREEN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit=UNITLESS,
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit=UNITLESS,
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit="RFU",
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="passive reference dye fluorescence",
                                                unit="RFU",
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
                                            )
                                        ],
                                        measures=[
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="reporter dye fluorescence",
                                                unit=UNITLESS,
                                            ),
                                            TDatacubeComponent(
                                                field_componentDatatype=FieldComponentDatatype.double,
                                                concept="slope",
                                                unit=UNITLESS,
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
            calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                calculated_data_document=[],
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )


def get_genotyping_data(file_name: str) -> Data:
    well_id = 0
    well_item_id = 1
    target1 = "CYP19_2-Allele 1"
    target2 = "CYP19_2-Allele 2"
    header = Header(
        measurement_time="2010-09-16 07:35:29 AM EDT",
        plate_well_count=96,
        barcode=None,
        device_identifier="Sponge_Bob_32",
        model_number="QuantStudio(TM) 7 Flex System",
        device_serial_number="123456789",
        analyst=None,
        experimental_data_identifier="QuantStudio 96-Well SNP Genotyping Example",
        experiment_type=ExperimentType.genotyping_qPCR_experiment,
        measurement_method_identifier="Ct",
        pcr_detection_chemistry="TAQMAN",
        passive_reference_dye_setting="ROX",
    )
    amp_data = {
        well_item_id: {
            target1: AmplificationData(
                total_cycle_number_setting=2,
                cycle=[1, 2],
                rn=[0.275, 0.277],
                delta_rn=[-0.003, -0.001],
            ),
            target2: AmplificationData(
                total_cycle_number_setting=2,
                cycle=[1, 2],
                rn=[0.825, 0.831],
                delta_rn=[-0.016, -0.011],
            ),
        }
    }
    result_data = {
        well_item_id: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.219,
                cycle_threshold_result=None,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=0.016,
                genotyping_determination_result="Negative Control (NC)",
                genotyping_determination_method_setting=None,
                quantity=None,
                quantity_mean=None,
                quantity_sd=None,
                ct_mean=None,
                ct_sd=None,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=None,
                rq_min=None,
                rq_max=None,
                rn_mean=None,
                rn_sd=None,
                y_intercept=None,
                r_squared=None,
                slope=None,
                efficiency=None,
            ),
            target2.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.132,
                cycle_threshold_result=None,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=0.029,
                genotyping_determination_result="Negative Control (NC)",
                genotyping_determination_method_setting=None,
                quantity=None,
                quantity_mean=None,
                quantity_sd=None,
                ct_mean=None,
                ct_sd=None,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=None,
                rq_min=None,
                rq_max=None,
                rn_mean=None,
                rn_sd=None,
                y_intercept=None,
                r_squared=None,
                slope=None,
                efficiency=None,
            ),
        }
    }
    result_metadata = ResultMetadata(
        reference_dna_description=None,
        reference_sample_description=None,
    )
    well = Well(
        identifier=well_id,
        items=[
            WellItem(
                uuid="3c40d2c2-0a64-433f-b639-e9c6e896313e",
                identifier=well_item_id,
                position="A1",
                target_dna_description=target1,
                sample_identifier="NTC",
                well_location_identifier="A1",
                reporter_dye_setting="VIC",
                quencher_dye_setting=None,
                sample_role_type="NTC",
            ),
            WellItem(
                uuid="cba0ba82-1486-4e0c-90ec-2abdfaf254b0",
                identifier=well_item_id,
                position="A1",
                target_dna_description=target2,
                sample_identifier="NTC",
                well_location_identifier="A1",
                reporter_dye_setting="FAM",
                quencher_dye_setting=None,
                sample_role_type="NTC",
            ),
        ],
    )

    return _create_data(
        file_name,
        header,
        wells=[well],
        amp_data=amp_data,
        multi_data={},
        results_data=result_data,
        results_metadata=result_metadata,
        melt_data={},
        calculated_documents=[],
    )


def get_genotyping_model() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="Sponge_Bob_32",
                model_number="QuantStudio(TM) 7 Flex System",
                device_serial_number="123456789",
            ),
            qPCR_document=[
                QPCRDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        plate_well_count=TQuantityValueNumber(
                            value=96,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="3c40d2c2-0a64-433f-b639-e9c6e896313e",
                                measurement_time="2010-09-16T07:35:29-04:00",
                                target_DNA_description="CYP19_2-Allele 1",
                                sample_document=SampleDocument(
                                    sample_identifier="NTC",
                                    sample_role_type="NTC",
                                    well_location_identifier="A1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            PCR_detection_chemistry="TAQMAN",
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=2.0
                                            ),
                                            reporter_dye_setting="VIC",
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
                                                            unit=UNITLESS,
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
                                                            unit=UNITLESS,
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
                                measurement_identifier="cba0ba82-1486-4e0c-90ec-2abdfaf254b0",
                                measurement_time="2010-09-16T07:35:29-04:00",
                                target_DNA_description="CYP19_2-Allele 2",
                                sample_document=SampleDocument(
                                    sample_identifier="NTC",
                                    sample_role_type="NTC",
                                    well_location_identifier="A1",
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            PCR_detection_chemistry="TAQMAN",
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=2.0
                                            ),
                                            reporter_dye_setting="FAM",
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
                                                            unit=UNITLESS,
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
                                                            unit=UNITLESS,
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
            calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                calculated_data_document=[],
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )


def get_rel_std_curve_data(file_name: str) -> Data:
    well_id_1 = 37
    well_id_2 = 38
    well_item_id_1 = 37
    well_item_id_2 = 38
    target1 = "RNaseP"
    header = Header(
        measurement_time="2010-10-20 02:23:34 AM EDT",
        plate_well_count=96,
        experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
        device_identifier="278880034",
        model_number="QuantStudio(TM) 7 Flex System",
        device_serial_number="278880034",
        measurement_method_identifier="Ct",
        pcr_detection_chemistry="TAQMAN",
        passive_reference_dye_setting="ROX",
        barcode="",
        analyst=None,
        experimental_data_identifier="QuantStudio96-Well Relative Standard Curve Example",
    )
    amp_data = {
        well_item_id_1: {
            target1: AmplificationData(
                total_cycle_number_setting=1.0,
                cycle=[1],
                rn=[0.627],
                delta_rn=[0.001],
            ),
        },
        well_item_id_2: {
            target1: AmplificationData(
                total_cycle_number_setting=1.0,
                cycle=[1],
                rn=[0.612],
                delta_rn=[-0.001],
            ),
        },
    }
    result_data = {
        well_item_id_1: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.133,
                cycle_threshold_result=30.155,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
                quantity=794.91,
                quantity_mean=818.012,
                quantity_sd=29.535,
                ct_mean=30.115,
                ct_sd=0.051,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=0.798,
                rq_min=0.658,
                rq_max=0.967,
                rn_mean=None,
                rn_sd=None,
                y_intercept=39.662,
                r_squared=0.999,
                slope=-3.278,
                efficiency=101.866,
            )
        },
        well_item_id_2: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.133,
                cycle_threshold_result=30.2,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
                quantity=769.776,
                quantity_mean=818.012,
                quantity_sd=29.535,
                ct_mean=30.115,
                ct_sd=0.051,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=0.798,
                rq_min=0.658,
                rq_max=0.967,
                rn_mean=None,
                rn_sd=None,
                y_intercept=39.662,
                r_squared=0.999,
                slope=-3.278,
                efficiency=101.866,
            )
        },
    }
    result_metadata = ResultMetadata(
        reference_dna_description="RNaseP",
        reference_sample_description="800",
    )
    wells = [
        Well(
            identifier=well_id_1,
            items=[
                WellItem(
                    uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                    identifier=well_item_id_1,
                    target_dna_description=target1,
                    sample_identifier="800",
                    reporter_dye_setting="FAM",
                    position="D1",
                    well_location_identifier="D1",
                    quencher_dye_setting="NFQ-MGB",
                    sample_role_type="UNKNOWN",
                )
            ],
        ),
        Well(
            identifier=well_id_2,
            items=[
                WellItem(
                    uuid="f112727d-c267-4061-b51e-a0784a112afe",
                    identifier=well_item_id_2,
                    target_dna_description=target1,
                    sample_identifier="800",
                    reporter_dye_setting="FAM",
                    position="D2",
                    well_location_identifier="D2",
                    quencher_dye_setting="NFQ-MGB",
                    sample_role_type="UNKNOWN",
                )
            ],
        ),
    ]
    calculated_documents = [
        CalculatedDocument(
            uuid="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
            name="quantity mean",
            value=818.012,
            data_sources=[
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocument(
                        uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
                        name="quantity",
                        value=794.91,
                        data_sources=[
                            DataSource(
                                feature="cycle threshold result",
                                reference=Referenceable(
                                    uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8"
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                ),
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocument(
                        uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                        name="quantity",
                        value=769.776,
                        data_sources=[
                            DataSource(
                                feature="cycle threshold result",
                                reference=Referenceable(
                                    uuid="f112727d-c267-4061-b51e-a0784a112afe",
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                ),
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
            name="quantity",
            value=794.91,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                    ),
                )
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
            name="quantity",
            value=769.776,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="f112727d-c267-4061-b51e-a0784a112afe",
                    ),
                )
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="4da4ba6b-cb9d-471b-b810-fdc46f57528e",
            name="quantity sd",
            value=29.535,
            data_sources=[
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocument(
                        uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
                        name="quantity",
                        value=794.91,
                        data_sources=[
                            DataSource(
                                feature="cycle threshold result",
                                reference=Referenceable(
                                    uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                ),
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocument(
                        uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                        name="quantity",
                        value=769.776,
                        data_sources=[
                            DataSource(
                                feature="cycle threshold result",
                                reference=Referenceable(
                                    uuid="f112727d-c267-4061-b51e-a0784a112afe",
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                ),
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="a59289c2-e71a-4d72-972d-258e3ac2e78e",
            name="ct mean",
            value=30.115,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                    ),
                ),
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="f112727d-c267-4061-b51e-a0784a112afe",
                    ),
                ),
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="99f04b2e-4463-4666-b20d-d8f1de2f62e5",
            name="ct sd",
            value=0.051,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                    ),
                ),
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="f112727d-c267-4061-b51e-a0784a112afe",
                    ),
                ),
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="095631c4-1c21-412d-acc1-3a67984dbbf2",
            name="rq min",
            value=0.658,
            data_sources=[
                DataSource(
                    feature="rq",
                    reference=CalculatedDocument(
                        uuid="d0dc238e-13a6-4057-b1ae-c8d30145805b",
                        name="rq",
                        value=0.798,
                        data_sources=[
                            DataSource(
                                feature="quantity mean",
                                reference=CalculatedDocument(
                                    uuid="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
                                    name="quantity mean",
                                    value=818.012,
                                    data_sources=[
                                        DataSource(
                                            feature="quantity",
                                            reference=CalculatedDocument(
                                                uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
                                                name="quantity",
                                                value=794.91,
                                                data_sources=[
                                                    DataSource(
                                                        feature="cycle threshold result",
                                                        reference=Referenceable(
                                                            uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                                        ),
                                                    )
                                                ],
                                                iterated=True,
                                            ),
                                        ),
                                        DataSource(
                                            feature="quantity",
                                            reference=CalculatedDocument(
                                                uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                                                name="quantity",
                                                value=769.776,
                                                data_sources=[
                                                    DataSource(
                                                        feature="cycle threshold result",
                                                        reference=Referenceable(
                                                            uuid="f112727d-c267-4061-b51e-a0784a112afe",
                                                        ),
                                                    )
                                                ],
                                                iterated=True,
                                            ),
                                        ),
                                    ],
                                    iterated=True,
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                )
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="d0dc238e-13a6-4057-b1ae-c8d30145805b",
            name="rq",
            value=0.798,
            data_sources=[
                DataSource(
                    feature="quantity mean",
                    reference=CalculatedDocument(
                        uuid="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
                        name="quantity mean",
                        value=818.012,
                        data_sources=[
                            DataSource(
                                feature="quantity",
                                reference=CalculatedDocument(
                                    uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
                                    name="quantity",
                                    value=794.91,
                                    data_sources=[
                                        DataSource(
                                            feature="cycle threshold result",
                                            reference=Referenceable(
                                                uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                            ),
                                        )
                                    ],
                                    iterated=True,
                                ),
                            ),
                            DataSource(
                                feature="quantity",
                                reference=CalculatedDocument(
                                    uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                                    name="quantity",
                                    value=769.776,
                                    data_sources=[
                                        DataSource(
                                            feature="cycle threshold result",
                                            reference=Referenceable(
                                                uuid="f112727d-c267-4061-b51e-a0784a112afe",
                                            ),
                                        )
                                    ],
                                    iterated=True,
                                ),
                            ),
                        ],
                        iterated=True,
                    ),
                )
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="4db4a552-e3c5-49fc-ab02-759245c01a48",
            name="rq max",
            value=0.967,
            data_sources=[
                DataSource(
                    feature="rq",
                    reference=CalculatedDocument(
                        uuid="d0dc238e-13a6-4057-b1ae-c8d30145805b",
                        name="rq",
                        value=0.798,
                        data_sources=[
                            DataSource(
                                feature="quantity mean",
                                reference=CalculatedDocument(
                                    uuid="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
                                    name="quantity mean",
                                    value=818.012,
                                    data_sources=[
                                        DataSource(
                                            feature="quantity",
                                            reference=CalculatedDocument(
                                                uuid="61d96780-4aa9-4d24-8ff5-491ccd325502",
                                                name="quantity",
                                                value=794.91,
                                                data_sources=[
                                                    DataSource(
                                                        feature="cycle threshold result",
                                                        reference=Referenceable(
                                                            uuid="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                                        ),
                                                    )
                                                ],
                                                iterated=True,
                                            ),
                                        ),
                                        DataSource(
                                            feature="quantity",
                                            reference=CalculatedDocument(
                                                uuid="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                                                name="quantity",
                                                value=769.776,
                                                data_sources=[
                                                    DataSource(
                                                        feature="cycle threshold result",
                                                        reference=Referenceable(
                                                            uuid="f112727d-c267-4061-b51e-a0784a112afe",
                                                        ),
                                                    )
                                                ],
                                                iterated=True,
                                            ),
                                        ),
                                    ],
                                    iterated=True,
                                ),
                            )
                        ],
                        iterated=True,
                    ),
                )
            ],
            iterated=True,
        ),
    ]
    return _create_data(
        file_name,
        header,
        wells=wells,
        amp_data=amp_data,
        multi_data={},
        results_data=result_data,
        results_metadata=result_metadata,
        melt_data={},
        calculated_documents=calculated_documents,
    )


def get_rel_std_curve_model() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="278880034",
                model_number="QuantStudio(TM) 7 Flex System",
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
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                measurement_time="2010-10-20T02:23:34-04:00",
                                target_DNA_description="RNaseP",
                                sample_document=SampleDocument(
                                    sample_identifier="800",
                                    batch_identifier=None,
                                    sample_role_type="UNKNOWN",
                                    well_location_identifier="D1",
                                    well_plate_identifier="",
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            PCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
                                                unit="#",
                                                has_statistic_datum_role=None,
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
                                                    value=0.133,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=None,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=30.155,
                                                unit=UNITLESS,
                                                has_statistic_datum_role=None,
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
                                                            unit=UNITLESS,
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.627]],  # type: ignore[list-item]
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
                                                            unit=UNITLESS,
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.001]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result=None,
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=None,
                                passive_reference_dye_data_cube=None,
                                melting_curve_data_cube=None,
                            )
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="QuantStudio96-Well Relative Standard Curve Example",
                        experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                        well_volume=None,
                    ),
                    analyst=None,
                    submitter=None,
                    calculated_data_aggregate_document=None,
                ),
                QPCRDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        plate_well_count=TQuantityValueNumber(
                            value=96,
                            unit="#",
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="f112727d-c267-4061-b51e-a0784a112afe",
                                measurement_time="2010-10-20T02:23:34-04:00",
                                target_DNA_description="RNaseP",
                                sample_document=SampleDocument(
                                    sample_identifier="800",
                                    batch_identifier=None,
                                    sample_role_type="UNKNOWN",
                                    well_location_identifier="D2",
                                    well_plate_identifier="",
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            PCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
                                                unit="#",
                                                has_statistic_datum_role=None,
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
                                                    value=0.133,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=None,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=30.2,
                                                unit=UNITLESS,
                                                has_statistic_datum_role=None,
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
                                                            unit=UNITLESS,
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
                                                            unit=UNITLESS,
                                                            scale=None,
                                                            field_asm_fill_value=None,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[-0.001]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result=None,
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=None,
                                passive_reference_dye_data_cube=None,
                                melting_curve_data_cube=None,
                            )
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="QuantStudio96-Well Relative Standard Curve Example",
                        experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                        well_volume=None,
                    ),
                    analyst=None,
                    submitter=None,
                    calculated_data_aggregate_document=None,
                ),
            ],
            data_system_document=DataSystemDocument(
                data_system_instance_identifier="localhost",
                file_name="appbio_quantstudio_test04.txt",
                UNC_path="",
                software_name="Thermo QuantStudio",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
            calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                calculated_data_document=[
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="61d96780-4aa9-4d24-8ff5-491ccd325502",
                                    data_source_feature="quantity",
                                ),
                                DataSourceDocumentItem(
                                    data_source_identifier="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                                    data_source_feature="quantity",
                                ),
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="quantity mean",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=818.012,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="61d96780-4aa9-4d24-8ff5-491ccd325502",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                    data_source_feature="cycle threshold result",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="quantity",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=794.91,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="f112727d-c267-4061-b51e-a0784a112afe",
                                    data_source_feature="cycle threshold result",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="quantity",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=769.776,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="4da4ba6b-cb9d-471b-b810-fdc46f57528e",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="61d96780-4aa9-4d24-8ff5-491ccd325502",
                                    data_source_feature="quantity",
                                ),
                                DataSourceDocumentItem(
                                    data_source_identifier="c9f7ba93-faff-465c-b1b6-baa049cab34f",
                                    data_source_feature="quantity",
                                ),
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="quantity sd",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=29.535,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="a59289c2-e71a-4d72-972d-258e3ac2e78e",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                    data_source_feature="cycle threshold result",
                                ),
                                DataSourceDocumentItem(
                                    data_source_identifier="f112727d-c267-4061-b51e-a0784a112afe",
                                    data_source_feature="cycle threshold result",
                                ),
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="ct mean",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=30.115,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="99f04b2e-4463-4666-b20d-d8f1de2f62e5",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="3387cf01-0e74-4636-8c1c-cfe840d7aff8",
                                    data_source_feature="cycle threshold result",
                                ),
                                DataSourceDocumentItem(
                                    data_source_identifier="f112727d-c267-4061-b51e-a0784a112afe",
                                    data_source_feature="cycle threshold result",
                                ),
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="ct sd",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.051,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="095631c4-1c21-412d-acc1-3a67984dbbf2",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="d0dc238e-13a6-4057-b1ae-c8d30145805b",
                                    data_source_feature="rq",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="rq min",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.658,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="d0dc238e-13a6-4057-b1ae-c8d30145805b",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="5c16ac3d-02de-4d5b-b42e-707fb2043d95",
                                    data_source_feature="quantity mean",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="rq",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.798,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="4db4a552-e3c5-49fc-ab02-759245c01a48",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="d0dc238e-13a6-4057-b1ae-c8d30145805b",
                                    data_source_feature="rq",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="rq max",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.967,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                ]
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )


def get_broken_calc_doc_data(file_name: str) -> Data:
    well_id = 37
    well_item_id = 37
    target1 = "RNaseP"
    header = Header(
        measurement_time="2010-10-20 02:23:34 AM EDT",
        plate_well_count=96,
        experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
        device_identifier="278880034",
        model_number="QuantStudio(TM) 7 Flex System",
        device_serial_number="278880034",
        measurement_method_identifier="Ct",
        pcr_detection_chemistry="TAQMAN",
        passive_reference_dye_setting="ROX",
        barcode="",
        analyst=None,
        experimental_data_identifier="QuantStudio96-Well Relative Standard Curve Example",
    )
    amp_data = {
        well_item_id: {
            target1: AmplificationData(
                total_cycle_number_setting=1.0,
                cycle=[1],
                rn=[0.627],
                delta_rn=[0.001],
            ),
        }
    }
    result_data = {
        well_item_id: {
            target1.replace(" ", ""): Result(
                cycle_threshold_value_setting=0.133,
                cycle_threshold_result=30.155,
                automatic_cycle_threshold_enabled_setting=True,
                automatic_baseline_determination_enabled_setting=True,
                normalized_reporter_result=None,
                baseline_corrected_reporter_result=None,
                genotyping_determination_result=None,
                genotyping_determination_method_setting=None,
                quantity=None,
                quantity_mean=818.012,
                quantity_sd=29.535,
                ct_mean=30.115,
                ct_sd=0.051,
                delta_ct_mean=None,
                delta_ct_se=None,
                delta_delta_ct=None,
                rq=0.798,
                rq_min=0.658,
                rq_max=0.967,
                rn_mean=None,
                rn_sd=None,
                y_intercept=39.662,
                r_squared=0.999,
                slope=-3.278,
                efficiency=101.866,
            )
        }
    }
    result_metadata = ResultMetadata(
        reference_dna_description="RNaseP",
        reference_sample_description="800",
    )
    well = Well(
        identifier=well_id,
        items=[
            WellItem(
                uuid="a1453d7a-dd6b-4630-923f-7e4a14a7ee70",
                identifier=well_item_id,
                position="D1",
                target_dna_description=target1,
                sample_identifier="800",
                well_location_identifier="D1",
                reporter_dye_setting="FAM",
                quencher_dye_setting="NFQ-MGB",
                sample_role_type="UNKNOWN",
            )
        ],
    )
    calculated_documents = [
        CalculatedDocument(
            uuid="f8cb25cf-8052-40eb-aead-1b6d371b9f25",
            name="ct mean",
            value=30.115,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="ba6db637-e3c9-4c08-bb0d-86b5cf1a14ab",
                    ),
                )
            ],
            iterated=True,
        ),
        CalculatedDocument(
            uuid="d6d4d929-aa30-414b-a56a-12d2cac78bb3",
            name="ct sd",
            value=0.051,
            data_sources=[
                DataSource(
                    feature="cycle threshold result",
                    reference=Referenceable(
                        uuid="a1453d7a-dd6b-4630-923f-7e4a14a7ee70",
                    ),
                )
            ],
            iterated=True,
        ),
    ]

    return _create_data(
        file_name,
        header,
        wells=[well],
        amp_data=amp_data,
        multi_data={},
        results_data=result_data,
        results_metadata=result_metadata,
        melt_data={},
        calculated_documents=calculated_documents,
    )


def get_broken_calc_doc_model() -> Model:
    return Model(
        qPCR_aggregate_document=QPCRAggregateDocument(
            device_system_document=DeviceSystemDocument(
                device_identifier="278880034",
                model_number="QuantStudio(TM) 7 Flex System",
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
                        ),
                        measurement_document=[
                            MeasurementDocumentItem(
                                measurement_identifier="a1453d7a-dd6b-4630-923f-7e4a14a7ee70",
                                measurement_time="2010-10-20T02:23:34-04:00",
                                target_DNA_description="RNaseP",
                                sample_document=SampleDocument(
                                    sample_identifier="800",
                                    batch_identifier=None,
                                    sample_role_type="UNKNOWN",
                                    well_location_identifier="D1",
                                    well_plate_identifier="",
                                    mass_concentration=None,
                                ),
                                device_control_aggregate_document=DeviceControlAggregateDocument(
                                    device_control_document=[
                                        DeviceControlDocumentItem(
                                            device_type="qPCR",
                                            measurement_method_identifier="Ct",
                                            PCR_detection_chemistry="TAQMAN",
                                            device_identifier=None,
                                            detection_type=None,
                                            total_cycle_number_setting=TQuantityValueNumber(
                                                value=1.0,
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
                                                    value=0.133,
                                                ),
                                                automatic_cycle_threshold_enabled_setting=True,
                                                automatic_baseline_determination_enabled_setting=True,
                                                baseline_determination_start_cycle_setting=None,
                                                baseline_determination_end_cycle_setting=None,
                                                genotyping_determination_method=None,
                                                genotyping_determination_method_setting=None,
                                            ),
                                            cycle_threshold_result=TNullableQuantityValueUnitless(
                                                value=30.155,
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="normalized report result",
                                                            unit=UNITLESS,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.627]],  # type: ignore[list-item]
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
                                                        )
                                                    ],
                                                    measures=[
                                                        TDatacubeComponent(
                                                            field_componentDatatype=FieldComponentDatatype.double,
                                                            concept="baseline corrected reporter result",
                                                            unit=UNITLESS,
                                                        )
                                                    ],
                                                ),
                                                data=TDatacubeData(
                                                    dimensions=[[1.0]],
                                                    measures=[[0.001]],  # type: ignore[list-item]
                                                    points=None,
                                                ),
                                            ),
                                            genotyping_determination_result=None,
                                        )
                                    ]
                                ),
                                reporter_dye_data_cube=None,
                                passive_reference_dye_data_cube=None,
                                melting_curve_data_cube=None,
                            )
                        ],
                        analytical_method_identifier=None,
                        experimental_data_identifier="QuantStudio96-Well Relative Standard Curve Example",
                        experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
                        container_type=ContainerType.qPCR_reaction_block,
                        well_volume=None,
                    ),
                    analyst=None,
                    submitter=None,
                    calculated_data_aggregate_document=None,
                )
            ],
            data_system_document=DataSystemDocument(
                data_system_instance_identifier="localhost",
                file_name="appbio_quantstudio_test05.txt",
                UNC_path="",
                software_name="Thermo QuantStudio",
                software_version="1.0",
                ASM_converter_name=ASM_CONVERTER_NAME,
                ASM_converter_version=ASM_CONVERTER_VERSION,
            ),
            calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                calculated_data_document=[
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="f8cb25cf-8052-40eb-aead-1b6d371b9f25",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="ba6db637-e3c9-4c08-bb0d-86b5cf1a14ab",
                                    data_source_feature="cycle threshold result",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="ct mean",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=30.115,
                            unit=UNITLESS,
                            has_statistic_datum_role=None,
                            field_type=None,
                        ),
                    ),
                    CalculatedDataDocumentItem(
                        calculated_data_identifier="d6d4d929-aa30-414b-a56a-12d2cac78bb3",
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier="a1453d7a-dd6b-4630-923f-7e4a14a7ee70",
                                    data_source_feature="cycle threshold result",
                                )
                            ]
                        ),
                        data_processing_document=DataProcessingDocument1(
                            reference_DNA_description="RNaseP",
                            reference_sample_description="800",
                        ),
                        calculated_data_name="ct sd",
                        calculated_data_description=None,
                        calculated_datum=TQuantityValueUnitless(
                            value=0.051,
                            unit=UNITLESS,
                        ),
                    ),
                ]
            ),
        ),
        manifest="http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest",
    )
