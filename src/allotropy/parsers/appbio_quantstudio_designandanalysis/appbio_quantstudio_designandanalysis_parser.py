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
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_data_creator import (
    create_data,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
    Well,
    WellItem,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class AppBioQuantStudioDesignandanalysisParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio QuantStudio Design & Analysis"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = DesignQuantstudioContents.create(named_file_contents)
        data = create_data(contents)
        return self._get_model(data, named_file_contents.original_file_name)

    def _get_model(self, data: Data, file_name: str) -> Model:
        return Model(
            qPCR_aggregate_document=QPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    product_manufacturer="ThermoFisher Scientific",
                    device_identifier=data.header.device_identifier,
                    model_number=data.header.model_number,
                    device_serial_number=data.header.device_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier="localhost",
                    file_name=file_name,
                    UNC_path="",  # unknown
                    software_name=data.header.software_name,
                    software_version=data.header.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                qPCR_document=[
                    QPCRDocumentItem(
                        analyst=data.header.analyst,
                        measurement_aggregate_document=self.get_measurement_aggregate_document(
                            data, well
                        ),
                    )
                    for well in data.wells
                ],
                calculated_data_aggregate_document=self.get_calculated_data_aggregate_document(
                    data
                ),
            )
        )

    def get_calculated_data_aggregate_document(
        self, data: Data
    ) -> TCalculatedDataAggregateDocument | None:
        if not data.calculated_documents:
            return None

        return TCalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calc_doc.uuid,
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=(
                                    data_source.reference.uuid
                                    if data_source.reference
                                    else None
                                ),
                                data_source_feature=data_source.feature,
                            )
                            for data_source in calc_doc.data_sources
                        ],
                    ),
                    data_processing_document=(
                        DataProcessingDocument1(
                            reference_DNA_description=data.reference_target,
                            reference_sample_description=data.reference_sample,
                        )
                        if data.experiment_type
                        == ExperimentType.relative_standard_curve_qPCR_experiment
                        else None
                    ),
                    calculated_data_name=calc_doc.name,
                    calculated_datum=TQuantityValueUnitless(value=calc_doc.value),
                )
                for calc_doc in data.calculated_documents
            ],
        )

    def get_measurement_aggregate_document(
        self, data: Data, well: Well
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            experimental_data_identifier=data.header.experimental_data_identifier,
            container_type=ContainerType.qPCR_reaction_block,
            plate_well_count=TQuantityValueNumber(value=data.header.plate_well_count),
            measurement_document=[
                self.get_measurement_document_item(data, well, well_item)
                for well_item in well.items.values()
            ],
        )

    def get_measurement_document_item(
        self, data: Data, well: Well, well_item: WellItem
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=well_item.uuid,
            measurement_time=self._get_date_time(data.header.measurement_time),
            target_DNA_description=well_item.target_dna_description,
            sample_document=self.get_sample_document(data, well_item),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    self.get_device_control_document_item(data, well_item),
                ],
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    self.get_processed_data_document(well_item),
                ]
            ),
            reporter_dye_data_cube=self.get_reporter_dye_data_cube(well, well_item),
            passive_reference_dye_data_cube=self.get_passive_reference_dye_data_cube(
                data, well
            ),
            melting_curve_data_cube=self.get_melting_curve_data_cube(well_item),
        )

    def get_sample_document(self, data: Data, well_item: WellItem) -> SampleDocument:
        return SampleDocument(
            sample_identifier=well_item.sample_identifier,
            sample_role_type=well_item.sample_role_type,
            well_location_identifier=well_item.well_location_identifier,
            well_plate_identifier=data.header.barcode,
        )

    def get_device_control_document_item(
        self, data: Data, well_item: WellItem
    ) -> DeviceControlDocumentItem:
        return DeviceControlDocumentItem(
            device_type="qPCR",
            measurement_method_identifier=data.header.measurement_method_identifier,
            total_cycle_number_setting=TQuantityValueNumber(
                value=well_item.amplification_data.total_cycle_number_setting,
            ),
            PCR_detection_chemistry=data.header.pcr_detection_chemistry,
            reporter_dye_setting=well_item.reporter_dye_setting,
            quencher_dye_setting=well_item.quencher_dye_setting,
            passive_reference_dye_setting=data.header.passive_reference_dye_setting,
        )

    def get_processed_data_document(
        self, well_item: WellItem
    ) -> ProcessedDataDocumentItem:
        return ProcessedDataDocumentItem(
            data_processing_document=self.get_data_processing_document(well_item),
            cycle_threshold_result=TNullableQuantityValueUnitless(
                value=well_item.result.cycle_threshold_result,
            ),
            normalized_reporter_result=quantity_or_none(
                TQuantityValueUnitless, well_item.result.normalized_reporter_result
            ),
            baseline_corrected_reporter_result=quantity_or_none(
                TQuantityValueUnitless,
                well_item.result.baseline_corrected_reporter_result,
            ),
            genotyping_determination_result=well_item.result.genotyping_determination_result,
            normalized_reporter_data_cube=NormalizedReporterDataCube(
                label="normalized reporter",
                cube_structure=TDatacubeStructure(
                    dimensions=[
                        TDatacubeComponent(
                            field_componentDatatype=FieldComponentDatatype.integer,
                            concept="cycle count",
                            unit="#",
                        ),
                    ],
                    measures=[
                        TDatacubeComponent(
                            field_componentDatatype=FieldComponentDatatype.double,
                            concept="normalized report result",
                            unit="(unitless)",
                        ),
                    ],
                ),
                data=TDatacubeData(
                    dimensions=[well_item.amplification_data.cycle],
                    measures=[well_item.amplification_data.rn],
                ),
            ),
            baseline_corrected_reporter_data_cube=BaselineCorrectedReporterDataCube(
                label="baseline corrected reporter",
                cube_structure=TDatacubeStructure(
                    dimensions=[
                        TDatacubeComponent(
                            field_componentDatatype=FieldComponentDatatype.integer,
                            concept="cycle count",
                            unit="#",
                        ),
                    ],
                    measures=[
                        TDatacubeComponent(
                            field_componentDatatype=FieldComponentDatatype.double,
                            concept="baseline corrected reporter result",
                            unit="(unitless)",
                        ),
                    ],
                ),
                data=TDatacubeData(
                    dimensions=[well_item.amplification_data.cycle],
                    measures=[well_item.amplification_data.delta_rn],
                ),
            ),
        )

    def get_data_processing_document(
        self, well_item: WellItem
    ) -> DataProcessingDocument:
        return DataProcessingDocument(
            automatic_cycle_threshold_enabled_setting=well_item.result.automatic_cycle_threshold_enabled_setting,
            cycle_threshold_value_setting=TQuantityValueUnitless(
                value=well_item.result.cycle_threshold_value_setting
            ),
            automatic_baseline_determination_enabled_setting=well_item.result.automatic_baseline_determination_enabled_setting,
            baseline_determination_start_cycle_setting=quantity_or_none(
                TQuantityValueNumber,
                well_item.result.baseline_determination_start_cycle_setting,
            ),
            baseline_determination_end_cycle_setting=quantity_or_none(
                TQuantityValueNumber,
                well_item.result.baseline_determination_end_cycle_setting,
            ),
            genotyping_determination_method_setting=quantity_or_none(
                TQuantityValueUnitless,
                well_item.result.genotyping_determination_method_setting,
            ),
        )

    def get_reporter_dye_data_cube(
        self, well: Well, well_item: WellItem
    ) -> ReporterDyeDataCube | None:
        if well.multicomponent_data is None or well_item.reporter_dye_setting is None:
            return None

        return ReporterDyeDataCube(
            label="reporter dye",
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.integer,
                        concept="cycle count",
                        unit="#",
                    ),
                ],
                measures=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.double,
                        concept="reporter dye fluorescence",
                        unit="RFU",
                    ),
                ],
            ),
            data=TDatacubeData(
                dimensions=[well.multicomponent_data.cycle],
                measures=[
                    well.multicomponent_data.get_column(well_item.reporter_dye_setting)
                ],
            ),
        )

    def get_passive_reference_dye_data_cube(
        self, data: Data, well: Well
    ) -> PassiveReferenceDyeDataCube | None:
        if (
            well.multicomponent_data is None
            or data.header.passive_reference_dye_setting is None
        ):
            return None

        return PassiveReferenceDyeDataCube(
            label="passive reference dye",
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.integer,
                        concept="cycle count",
                        unit="#",
                    ),
                ],
                measures=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.double,
                        concept="passive reference dye fluorescence",
                        unit="RFU",
                    ),
                ],
            ),
            data=TDatacubeData(
                dimensions=[well.multicomponent_data.cycle],
                measures=[
                    well.multicomponent_data.get_column(
                        data.header.passive_reference_dye_setting
                    )
                ],
            ),
        )

    def get_melting_curve_data_cube(
        self, well_item: WellItem
    ) -> MeltingCurveDataCube | None:
        if well_item.melt_curve_data is None:
            return None

        return MeltingCurveDataCube(
            label="melt curve",
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.double,
                        concept="temperature",
                        unit="degC",
                    ),
                ],
                measures=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.double,
                        concept="fluorescence",
                        unit="RFU",
                    ),
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype.double,
                        concept="derivative",
                        unit="unitless",
                    ),
                ],
            ),
            data=TDatacubeData(
                dimensions=[well_item.melt_curve_data.temperature],
                measures=[
                    well_item.melt_curve_data.fluorescence,
                    well_item.melt_curve_data.derivative,
                ],
            ),
        )
