from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueDegreeCelsius,
    TQuantityValueGramPerLiter,
    TQuantityValueMicrometer,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliliterPerLiter,
    TQuantityValueMillimeterOfMercury,
    TQuantityValueMillimolePerLiter,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValueMilliOsmolesPerKilogram,
    TQuantityValuePercent,
    TQuantityValuePH,
    TQuantityValueUnitless,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Analyte:
    name: str
    value: float
    unit: str

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Analyte):
            return False

        return self.name < other.name


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


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
    cell_type_processing_method: str | None = None
    cell_density_dilution_factor: float | None = None
    analytes: list[Analyte] | None = None

    # Errors
    errors: list[Error] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    analyst: str | None
    data_processing_time: str | None


@dataclass(frozen=True)
class Metadata:
    device_type: str
    device_identifier: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None

    file_name: str | None = None
    data_system_instance_identifier: str | None = None

    analyst: str | None = None
    measurement_time: str | None = None
    analytical_method_identifier: str | None = None
    method_version: str | None = None
    experimental_data_identifier: str | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_identifier=data.metadata.device_identifier,
                    product_manufacturer=data.metadata.product_manufacturer,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                solution_analyzer_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> SolutionAnalyzerDocumentItem:
        return SolutionAnalyzerDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                data_processing_time=self.get_date_time(
                    measurement_group.data_processing_time
                )
                if measurement_group.data_processing_time
                else None,
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        detection_type=measurement.detection_type,
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
            absorbance=quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit, measurement.absorbance
            ),
            pO2=quantity_or_none(TQuantityValueMillimeterOfMercury, measurement.po2),
            pCO2=quantity_or_none(TQuantityValueMillimeterOfMercury, measurement.pco2),
            carbon_dioxide_saturation=quantity_or_none(
                TQuantityValuePercent, measurement.carbon_dioxide_saturation
            ),
            oxygen_saturation=quantity_or_none(
                TQuantityValuePercent, measurement.oxygen_saturation
            ),
            pH=quantity_or_none(TQuantityValuePH, measurement.ph),
            temperature=quantity_or_none(
                TQuantityValueDegreeCelsius, measurement.temperature
            ),
            osmolality=quantity_or_none(
                TQuantityValueMilliOsmolesPerKilogram, measurement.osmolality
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            batch_identifier=measurement.batch_identifier,
            description=measurement.description,
        )

    def _create_analyte_document(self, analyte: Analyte) -> AnalyteDocument:
        if analyte.unit == "g/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                mass_concentration=TQuantityValueGramPerLiter(value=analyte.value),
            )
        elif analyte.unit == "mL/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                volume_concentration=TQuantityValueMilliliterPerLiter(
                    value=analyte.value
                ),
            )
        elif analyte.unit == "mmol/L":
            return AnalyteDocument(
                analyte_name=analyte.name,
                molar_concentration=TQuantityValueMillimolePerLiter(
                    value=analyte.value
                ),
            )
        elif analyte.unit == "U/L":
            if analyte.name == "ldh":
                return AnalyteDocument(
                    analyte_name=analyte.name,
                    molar_concentration=TQuantityValueMillimolePerLiter(
                        value=analyte.value * 0.0167
                        if analyte.value > 0
                        else analyte.value
                    ),
                )
            else:
                msg = f"Invalid unit for {analyte.name}: {analyte.unit}"
                raise AllotropeConversionError(msg)

        msg = f"Invalid unit for analyte: {analyte.unit}, value values are: g/L, mL/L, mmol/L"
        raise AllotropeConversionError(msg)

    def _create_processed_data_document(
        self, measurement: Measurement
    ) -> ProcessedDataAggregateDocument | None:
        processed_data_document = ProcessedDataDocumentItem(
            viability__cell_counter_=quantity_or_none(
                TQuantityValuePercent, measurement.viability
            ),
            total_cell_density__cell_counter_=quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter, measurement.total_cell_density
            ),
            viable_cell_density__cell_counter_=quantity_or_none(
                TQuantityValueMillionCellsPerMilliliter, measurement.viable_cell_density
            ),
            average_live_cell_diameter__cell_counter_=quantity_or_none(
                TQuantityValueMicrometer, measurement.average_live_cell_diameter
            ),
            total_cell_count=quantity_or_none(
                TQuantityValueCell, measurement.total_cell_count
            ),
            viable_cell_count=quantity_or_none(
                TQuantityValueCell, measurement.viable_cell_count
            ),
            data_processing_document=DataProcessingDocument(
                cell_type_processing_method=measurement.cell_type_processing_method,
                cell_density_dilution_factor=quantity_or_none(
                    TQuantityValueUnitless, measurement.cell_density_dilution_factor
                ),
            )
            if measurement.cell_type_processing_method
            or measurement.cell_density_dilution_factor is not None
            else None,
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
