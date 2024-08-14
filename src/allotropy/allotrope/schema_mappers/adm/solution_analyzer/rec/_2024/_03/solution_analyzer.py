from collections.abc import Callable
from dataclasses import dataclass

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueGramPerLiter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMilliliterPerLiter,
    TQuantityValueMillimolePerLiter,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Analyte:
    name: str
    value: float
    unit: str


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
    batch_identifier: str | None = None

    # Measurements
    absorbance: float | None = None
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


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        return Model(
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_identifier=data.metadata.device_identifier,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path="",
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
                    ),
                ]
            ),
            absorbance=quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit, measurement.absorbance
            ),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    self._create_analyte_document(analyte)
                    for analyte in measurement.analytes
                ]
            )
            if measurement.analytes
            else None,
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            batch_identifier=measurement.batch_identifier,
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
