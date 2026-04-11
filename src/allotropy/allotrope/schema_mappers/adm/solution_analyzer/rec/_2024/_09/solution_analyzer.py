from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models_v2.adm.core.rec._2024._09.core import (
    TQuantityValue,
    TQuantityValueCell,
    TQuantityValueCountsPermL,
    TQuantityValueDegC,
    TQuantityValueGPerL,
    TQuantityValueMAU,
    TQuantityValueMicrom,
    TQuantityValueML,
    TQuantityValueMLPerL,
    TQuantityValueMmHg,
    TQuantityValueMmolPerL,
    TQuantityValueMosmPerkg,
    TQuantityValueOne06cellsPermL,
    TQuantityValuePercent,
    TQuantityValuePH,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models_v2.adm.core.rec._2024._09.hierarchy import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
)
from allotropy.allotrope.models_v2.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    DataProcessingDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DistributionAggregateDocument,
    DistributionDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError


@dataclass(frozen=True)
class Analyte:
    name: str
    value: float
    unit: str

    # Custom information document fields
    custom_info: dict[str, Any] | None = None

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return False

        return self.name < other.name


@dataclass(frozen=True)
class DistributionDocument:
    particle_size: float
    cumulative_count: float
    cumulative_particle_density: float
    differential_particle_density: float
    differential_count: float
    distribution_identifier: str
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


@dataclass(frozen=True)
class DataProcessing:
    cell_type_processing_method: str | None = None
    cell_density_dilution_factor: float | None = None
    dilution_factor_setting: float | None = None
    data_processing_omission_setting: bool | None = None


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    identifier: str
    measurement_time: str
    sample_identifier: str
    description: str | None = None
    batch_identifier: str | None = None
    detection_type: str | None = None

    # Measurements
    absorbance: float | None = None
    po2: float | None = None
    pco2: float | None = None
    carbon_dioxide_saturation: float | None = None
    oxygen_saturation: float | None = None
    ph: float | None = None
    temperature: float | None = None
    osmolality: float | None = None
    viability: float | None = None
    total_cell_density: float | None = None
    viable_cell_density: float | None = None
    average_live_cell_diameter: float | None = None
    total_cell_count: float | None = None
    viable_cell_count: float | None = None
    analytes: list[Analyte] | None = None
    data_processing: DataProcessing | None = None
    distribution_documents: list[DistributionDocument] | None = None

    # Errors
    errors: list[Error] | None = None
    custom_info: dict[str, Any] | None = None
    device_control_custom_info: dict[str, Any] | None = None
    sample_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    analyst: str | None
    data_processing_time: str | None
    errors: list[Error] | None = None


@dataclass(frozen=True)
class Metadata:
    device_type: str
    asm_file_identifier: str
    data_system_instance_identifier: str
    unc_path: str
    device_identifier: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    detection_type: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    file_name: str | None = None
    analyst: str | None = None
    measurement_time: str | None = None
    analytical_method_identifier: str | None = None
    method_version: str | None = None
    experimental_data_identifier: str | None = None
    flush_volume_setting: float | None = None
    detector_view_volume: float | None = None
    repetition_setting: int | None = None
    sample_volume_setting: float | None = None
    custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class DataSource:
    identifier: str
    feature: str


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_sources: list[DataSource]


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDataItem] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/09/solution-analyzer.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest=self.MANIFEST,
            solution_analyzer_aggregate_document=add_custom_information_document(
                SolutionAnalyzerAggregateDocument(
                    device_system_document=add_custom_information_document(
                        DeviceSystemDocument(
                            model_number=data.metadata.model_number,
                            equipment_serial_number=data.metadata.equipment_serial_number,
                            device_identifier=data.metadata.device_identifier,
                            product_manufacturer=data.metadata.product_manufacturer,
                        ),
                        None,
                    ),
                    data_system_document=add_custom_information_document(
                        DataSystemDocument(
                            asm_file_identifier=data.metadata.asm_file_identifier,
                            data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                            file_name=data.metadata.file_name,
                            unc_path=data.metadata.unc_path,
                            software_name=data.metadata.software_name,
                            software_version=data.metadata.software_version,
                            asm_converter_name=self.converter_name,
                            asm_converter_version=ASM_CONVERTER_VERSION,
                        ),
                        None,
                    ),
                    solution_analyzer_document=[
                        self._get_technique_document(measurement_group, data.metadata)
                        for measurement_group in data.measurement_groups
                    ],
                    calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                        data.calculated_data
                    ),
                ),
                None,
            ),
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> SolutionAnalyzerDocumentItem:
        return SolutionAnalyzerDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    data_processing_time=self.get_date_time(
                        measurement_group.data_processing_time
                    )
                    if measurement_group.data_processing_time
                    else None,
                    measurement_document=[
                        self._get_measurement_document_item(measurement, metadata)
                        for measurement in measurement_group.measurements
                    ],
                    error_aggregate_document=self._get_error_aggregate_document(
                        measurement_group.errors
                    ),
                ),
                None,
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItem:
        return add_custom_information_document(
            MeasurementDocumentItem(
                measurement_identifier=measurement.identifier,
                measurement_time=self.get_date_time(measurement.measurement_time),
                sample_document=self._get_sample_document(measurement),
                device_control_aggregate_document=DeviceControlAggregateDocument(
                    device_control_document=[
                        add_custom_information_document(
                            DeviceControlDocumentItem(
                                device_type=metadata.device_type,
                                detection_type=measurement.detection_type,
                                flush_volume_setting=(
                                    TQuantityValueML(
                                        value=metadata.flush_volume_setting
                                    )
                                    if metadata.flush_volume_setting is not None
                                    else None
                                ),
                                detector_view_volume=(
                                    TQuantityValueML(
                                        value=metadata.detector_view_volume
                                    )
                                    if metadata.detector_view_volume is not None
                                    else None
                                ),
                                repetition_setting=metadata.repetition_setting,
                                sample_volume_setting=(
                                    TQuantityValueML(
                                        value=metadata.sample_volume_setting
                                    )
                                    if metadata.sample_volume_setting is not None
                                    else None
                                ),
                            ),
                            measurement.device_control_custom_info,
                        ),
                    ]
                ),
                analyte_aggregate_document=AnalyteAggregateDocument(
                    analyte_document=[
                        self._create_analyte_document(analyte)
                        for analyte in measurement.analytes
                    ]
                )
                if measurement.analytes
                else None,
                processed_data_aggregate_document=self._create_processed_data_document(
                    measurement
                ),
                error_aggregate_document=self._get_error_aggregate_document(
                    measurement.errors
                ),
                absorbance=(
                    TQuantityValueMAU(value=measurement.absorbance)
                    if measurement.absorbance is not None
                    else None
                ),
                p_o2=(
                    TQuantityValueMmHg(value=measurement.po2)
                    if measurement.po2 is not None
                    else None
                ),
                p_co2=(
                    TQuantityValueMmHg(value=measurement.pco2)
                    if measurement.pco2 is not None
                    else None
                ),
                carbon_dioxide_saturation=(
                    TQuantityValuePercent(value=measurement.carbon_dioxide_saturation)
                    if measurement.carbon_dioxide_saturation is not None
                    else None
                ),
                oxygen_saturation=(
                    TQuantityValuePercent(value=measurement.oxygen_saturation)
                    if measurement.oxygen_saturation is not None
                    else None
                ),
                p_h=(
                    TQuantityValuePH(value=measurement.ph)
                    if measurement.ph is not None
                    else None
                ),
                temperature=(
                    TQuantityValueDegC(value=measurement.temperature)
                    if measurement.temperature is not None
                    else None
                ),
                osmolality=(
                    TQuantityValueMosmPerkg(value=measurement.osmolality)
                    if measurement.osmolality is not None
                    else None
                ),
            ),
            measurement.custom_info,
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
                description=measurement.description,
            ),
            measurement.sample_custom_info,
        )

    def _create_analyte_document(self, analyte: Analyte) -> AnalyteDocumentItem:
        output: AnalyteDocumentItem
        if analyte.unit == "g/L":
            output = AnalyteDocumentItem(
                analyte_name=analyte.name,
                mass_concentration=TQuantityValueGPerL(value=analyte.value),
            )
        elif analyte.unit == "mL/L":
            output = AnalyteDocumentItem(
                analyte_name=analyte.name,
                volume_concentration=TQuantityValueMLPerL(value=analyte.value),
            )
        elif analyte.unit == "mmol/L":
            output = AnalyteDocumentItem(
                analyte_name=analyte.name,
                molar_concentration=TQuantityValueMmolPerL(value=analyte.value),
            )
        elif analyte.unit == "U/L":
            if analyte.name == "ldh":
                output = AnalyteDocumentItem(
                    analyte_name=analyte.name,
                    molar_concentration=TQuantityValueMmolPerL(
                        value=analyte.value * 0.0167
                        if analyte.value > 0
                        else analyte.value,
                    ),
                )
            else:
                msg = f"Invalid unit for {analyte.name}: {analyte.unit}"
                raise AllotropeConversionError(msg)
        else:
            msg = f"Invalid unit for analyte: {analyte.unit}, possible values are: g/L, mL/L, mmol/L"
            raise AllotropeConversionError(msg)

        output = add_custom_information_document(output, analyte.custom_info or {})

        return output

    def _create_processed_data_document(
        self, measurement: Measurement
    ) -> ProcessedDataAggregateDocument | None:
        processed_data_document = add_custom_information_document(
            ProcessedDataDocumentItem(
                viability__cell_counter_=(
                    TQuantityValuePercent(value=measurement.viability)
                    if measurement.viability is not None
                    else None
                ),
                total_cell_density__cell_counter_=(
                    TQuantityValueOne06cellsPermL(value=measurement.total_cell_density)
                    if measurement.total_cell_density is not None
                    else None
                ),
                viable_cell_density__cell_counter_=(
                    TQuantityValueOne06cellsPermL(value=measurement.viable_cell_density)
                    if measurement.viable_cell_density is not None
                    else None
                ),
                average_live_cell_diameter__cell_counter_=(
                    TQuantityValueMicrom(value=measurement.average_live_cell_diameter)
                    if measurement.average_live_cell_diameter is not None
                    else None
                ),
                total_cell_count=(
                    TQuantityValueCell(value=measurement.total_cell_count)
                    if measurement.total_cell_count is not None
                    else None
                ),
                viable_cell_count=(
                    TQuantityValueCell(value=measurement.viable_cell_count)
                    if measurement.viable_cell_count is not None
                    else None
                ),
                data_processing_document=DataProcessingDocument(
                    cell_type_processing_method=measurement.data_processing.cell_type_processing_method,
                    cell_density_dilution_factor=(
                        TQuantityValueUnitless(
                            value=measurement.data_processing.cell_density_dilution_factor,
                        )
                        if measurement.data_processing.cell_density_dilution_factor
                        is not None
                        else None
                    ),
                    dilution_factor_setting=(
                        TQuantityValueUnitless(
                            value=measurement.data_processing.dilution_factor_setting,
                        )
                        if measurement.data_processing.dilution_factor_setting
                        is not None
                        else None
                    ),
                    data_processing_omission_setting=measurement.data_processing.data_processing_omission_setting,
                )
                if measurement.data_processing
                else None,
                distribution_aggregate_document=DistributionAggregateDocument(
                    distribution_document=[
                        add_custom_information_document(
                            DistributionDocumentItem(
                                distribution_identifier=distribution.distribution_identifier,
                                particle_size=TQuantityValueMicrom(
                                    value=distribution.particle_size
                                ),
                                cumulative_count=TQuantityValueUnitless(
                                    value=distribution.cumulative_count
                                ),
                                cumulative_particle_density=TQuantityValueCountsPermL(
                                    value=distribution.cumulative_particle_density
                                ),
                                differential_particle_density=TQuantityValueCountsPermL(
                                    value=distribution.differential_particle_density
                                ),
                                differential_count=TQuantityValueUnitless(
                                    value=distribution.differential_count
                                ),
                            ),
                            distribution.custom_info,
                        )
                        for distribution in measurement.distribution_documents
                    ]
                )
                if measurement.distribution_documents
                else None,
            ),
            None,
        )

        if all(value is None for value in processed_data_document.__dict__.values()):
            return None

        return ProcessedDataAggregateDocument(
            processed_data_document=[processed_data_document]
        )

    def _get_error_aggregate_document(
        self, errors: list[Error] | None
    ) -> ErrorAggregateDocument | None:
        if not errors:
            return None

        return ErrorAggregateDocument(
            error_document=[
                ErrorDocumentItem(error=error.error, error_feature=error.feature)
                for error in errors
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDataItem] | None
    ) -> CalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.identifier,
                    calculated_data_name=calculated_data_item.name,
                    calculated_result=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.identifier,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_sources
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
