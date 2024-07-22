from collections.abc import Callable
from typing import TypeVar

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
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    DataCube,
    Measurement,
    Metadata,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    create_data,
)
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
    try_int_or_nan,
)
from allotropy.parsers.vendor_parser import VendorParser

CubeClass = TypeVar("CubeClass")

class AppBioQuantStudioParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio QuantStudio RT-PCR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = LinesReader(lines)
        data = create_data(reader)
        file_name = named_file_contents.original_file_name
        return self._get_model(data, file_name)

    def _get_model(self, data: Data) -> Model:
        return Model(
            qPCR_aggregate_document=QPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    device_serial_number=data.metadata.device_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                qPCR_document=[
                    QPCRDocumentItem(
                        analyst=measurement_group.analyst,
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            experimental_data_identifier=measurement_group.experimental_data_identifier,
                            experiment_type=measurement_group.experiment_type,
                            container_type=measurement_group.container_type,
                            plate_well_count=TQuantityValueNumber(value=measurement_group.plate_well_count),
                            measurement_document=[
                                self.get_measurement_document_item(measurement, data.metadata)
                                for measurement in measurement_group.measurements
                            ],
                        ),
                    )
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self.get_outer_calculated_data_aggregate_document(
                    data
                ),
            )
        )

    def get_outer_calculated_data_aggregate_document(
        self, data: Data
    ) -> TCalculatedDataAggregateDocument:
        if data.header.experiment_type in [
            ExperimentType.comparative_CT_qPCR_experiment,
            ExperimentType.relative_standard_curve_qPCR_experiment,
        ]:
            data_processing_document = DataProcessingDocument1(
                reference_DNA_description=data.endogenous_control,
                reference_sample_description=data.reference_sample,
            )
        else:
            data_processing_document = None

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
                    data_processing_document=data_processing_document,
                    calculated_data_name=calc_doc.name,
                    calculated_data_description=None,
                    calculated_datum=TQuantityValueUnitless(value=calc_doc.value),
                )
                for calc_doc in data.calculated_documents
            ],
        )

    def get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata,
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self._get_date_time(measurement.timestamp),
            target_DNA_description=measurement.target_identifier,
            sample_document=SampleDocument(
                sample_identifier=measurement.sample_identifier,
                sample_role_type=measurement.sample_role_type,
                well_location_identifier=measurement.well_location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        measurement_method_identifier=metadata.measurement_method_identifier,
                        total_cycle_number_setting=TQuantityValueNumber(
                            value=measurement.total_cycle_number_setting,
                        ),
                        PCR_detection_chemistry=measurement.pcr_detection_chemistry,
                        reporter_dye_setting=measurement.reporter_dye_setting,
                        quencher_dye_setting=measurement.quencher_dye_setting,
                        passive_reference_dye_setting=measurement.passive_reference_dye_setting,
                    )
                ],
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[self.get_processed_data_document(measurement)],
            ),
            reporter_dye_data_cube=self._get_data_cube(ReporterDyeDataCube, "reporter dye", measurement),
            passive_reference_dye_data_cube=self._get_data_cube(PassiveReferenceDyeDataCube, "passive reference dye", measurement),
            melting_curve_data_cube=self._get_data_cube(MeltingCurveDataCube, "melting curve", measurement),
        )

    def get_processed_data_document(
        self, measurement: Measurement
    ) -> ProcessedDataDocumentItem:
        return ProcessedDataDocumentItem(
            data_processing_document=DataProcessingDocument(
                automatic_cycle_threshold_enabled_setting=measurement.automatic_baseline_determination_enabled_setting,
                cycle_threshold_value_setting=TQuantityValueUnitless(
                    value=measurement.cycle_threshold_value_setting,
                ),
                automatic_baseline_determination_enabled_setting=measurement.automatic_baseline_determination_enabled_setting,
                genotyping_determination_method_setting=quantity_or_none(
                    TQuantityValueUnitless,
                    measurement.genotyping_determination_method_setting,
                ),
            ),
            cycle_threshold_result=TNullableQuantityValueUnitless(
                value=measurement.cycle_threshold_result,
            ),
            normalized_reporter_result=quantity_or_none(
                TQuantityValueUnitless, measurement.normalized_reporter_result
            ),
            baseline_corrected_reporter_result=quantity_or_none(
                TQuantityValueUnitless,
                measurement.baseline_corrected_reporter_result,
            ),
            genotyping_determination_result=measurement.genotyping_determination_result,
            normalized_reporter_data_cube=self._get_data_cube(NormalizedReporterDataCube, "normalized reporter", measurement),
            baseline_corrected_reporter_data_cube=self._get_data_cube(NormalizedReporterDataCube, "baseline corrected reporter", measurement),
        )

    def _get_data_cube(self, cube_class: Callable[..., CubeClass], label: str, measurement: Measurement) -> CubeClass | None:
        data_cube = get_first_not_none(lambda cube: cube.label == label, measurement.data_cubes)
        if not data_cube:
            return None
        return cube_class(
            label=data_cube.label,
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(component.type_, component.concept, component.unit)
                    for component in data_cube.structure_dimensions
                ],
                measures=[
                    TDatacubeComponent(component.type_, component.concept, component.unit)
                    for component in data_cube.structure_measures
                ],
            ),
            data=TDatacubeData(
                dimensions=data_cube.dimensions,
                measures=data_cube.measures
            ),
        )
