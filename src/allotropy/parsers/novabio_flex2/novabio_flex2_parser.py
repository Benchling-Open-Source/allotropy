from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
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
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Data,
    Measurement,
    Metadata,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.novabio_flex2_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class NovaBioFlexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "NovaBio Flex2"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_model(create_data(named_file_contents))

    def _get_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest",
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                solution_analyzer_document=self._get_solution_analyzer_document(data),
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                    device_identifier=data.metadata.device_identifier,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
            ),
        )

    def _get_solution_analyzer_document(
        self, data: Data
    ) -> list[SolutionAnalyzerDocumentItem]:
        return [
            SolutionAnalyzerDocumentItem(
                analyst=group.analyst,
                measurement_aggregate_document=MeasurementAggregateDocument(
                    data_processing_time=self._get_date_time(group.data_processing_time),
                    measurement_document=self._get_measurements(group.measurements, data.metadata),
                ),
            )
            for group in data.measurement_groups
        ]

    def _get_measurements(
        self, measurements: list[Measurement], metadata: Metadata
    ) -> list[MeasurementDocument]:
        return [
            MeasurementDocument(
                measurement_identifier=measurement.identifier,
                measurement_time=self._get_date_time(measurement.measurement_time),
                sample_document=SampleDocument(
                    sample_identifier=measurement.sample_identifier,
                    description=measurement.description,
                    batch_identifier=measurement.batch_identifier,
                ),
                device_control_aggregate_document=DeviceControlAggregateDocument(
                    device_control_document=[
                        DeviceControlDocumentItem(
                            device_type=metadata.device_type, detection_type=measurement.detection_type
                        )
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
                processed_data_aggregate_document=self._create_processed_data_document(measurement),
                absorbance=quantity_or_none(
                    TQuantityValueMilliAbsorbanceUnit, measurement.absorbance
                ),
                pO2=quantity_or_none(
                    TQuantityValueMillimeterOfMercury, measurement.pO2
                ),
                pCO2=quantity_or_none(
                    TQuantityValueMillimeterOfMercury, measurement.pCO2
                ),
                carbon_dioxide_saturation=quantity_or_none(
                    TQuantityValuePercent, measurement.carbon_dioxide_saturation
                ),
                oxygen_saturation=quantity_or_none(
                    TQuantityValuePercent, measurement.oxygen_saturation
                ),
                pH=quantity_or_none(
                    TQuantityValuePH, measurement.pH
                ),
                temperature=quantity_or_none(
                    TQuantityValueDegreeCelsius, measurement.temperature
                ),
                osmolality=quantity_or_none(
                    TQuantityValueMilliOsmolesPerKilogram, measurement.osmolality
                )
            )
            for measurement in measurements
        ]

    def _create_processed_data_document(self, measurement: Measurement) -> ProcessedDataAggregateDocument | None:
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
            ) if measurement.cell_type_processing_method or measurement.cell_density_dilution_factor is not None else None
        )

        if all(value is None for value in processed_data_document.__dict__.values()):
            return None

        return ProcessedDataAggregateDocument(
            processed_data_document=[processed_data_document]
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
