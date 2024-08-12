from collections.abc import Callable
from dataclasses import dataclass

from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    CalibrationAggregateDocument,
    CalibrationDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    MultiAnalyteProfilingAggregateDocument,
    MultiAnalyteProfilingDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TDateTimeValue,
    TStatisticDatumRole,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Analyte:
    identifier: str
    name: str
    assay_bead_identifier: str
    assay_bead_count: float
    fluorescence: float


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

    # Settings
    assay_bead_count: float
    dilution_factor_setting: float

    # Processed data
    analytes: list[Analyte]

    # Optional metadata
    location_identifier: str | None = None

    # Errors
    errors: list[Error] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]


@dataclass(frozen=True)
class Calibration:
    name: str
    report: str
    time: str


@dataclass(frozen=True)
class Metadata:
    device_type: str
    file_name: str

    container_type: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    data_system_instance_identifier: str | None = None

    analyst: str | None = None
    analytical_method_identifier: str | None = None
    method_version: str | None = None
    experimental_data_identifier: str | None = None
    sample_volume_setting: float | None = None
    detector_gain_setting: str | None = None
    minimum_bead_count_setting: float | None = None
    plate_well_count: float | None = None

    calibrations: list[Calibration] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data) -> Model:
        return Model(
            multi_analyte_profiling_aggregate_document=MultiAnalyteProfilingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    calibration_aggregate_document=self._get_calibration_aggregate_document(
                        data.metadata.calibrations
                    ),
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                multi_analyte_profiling_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> MultiAnalyteProfilingDocumentItem:
        return MultiAnalyteProfilingDocumentItem(
            analyst=metadata.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                analytical_method_identifier=metadata.analytical_method_identifier,
                method_version=metadata.method_version,
                experimental_data_identifier=metadata.experimental_data_identifier,
                container_type=metadata.container_type,
                plate_well_count=quantity_or_none(
                    TQuantityValueNumber, metadata.plate_well_count
                ),
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_calibration_aggregate_document(
        self, calibrations: list[Calibration] | None
    ) -> CalibrationAggregateDocument | None:
        if not calibrations:
            return None

        return CalibrationAggregateDocument(
            calibration_document=[
                CalibrationDocumentItem(
                    calibration_name=calibration.name,
                    calibration_report=calibration.report,
                    calibration_time=self.get_date_time(calibration.time),
                )
                for calibration in calibrations
            ]
        )

    def _get_measurement_document_item(
        self,
        measurement: Measurement,
        metadata: Metadata,
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=measurement.identifier,
            measurement_time=self.get_date_time(measurement.measurement_time),
            sample_document=self._get_sample_document(measurement),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=metadata.device_type,
                        sample_volume_setting=quantity_or_none(
                            TQuantityValueMicroliter, metadata.sample_volume_setting
                        ),
                        dilution_factor_setting=TQuantityValueUnitless(
                            value=measurement.dilution_factor_setting
                        ),
                        detector_gain_setting=metadata.detector_gain_setting,
                        minimum_assay_bead_count_setting=quantity_or_none(
                            TQuantityValueNumber, metadata.minimum_bead_count_setting
                        ),
                    )
                ]
            ),
            assay_bead_count=TQuantityValueNumber(value=measurement.assay_bead_count),
            analyte_aggregate_document=self._get_analyte_aggregate_document(
                measurement.analytes
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
        )

    def _get_analyte_aggregate_document(
        self, analytes: list[Analyte]
    ) -> AnalyteAggregateDocument:
        return AnalyteAggregateDocument(
            analyte_document=[
                AnalyteDocumentItem(
                    analyte_identifier=analyte.identifier,
                    analyte_name=analyte.name,
                    assay_bead_identifier=analyte.assay_bead_identifier,
                    assay_bead_count=TQuantityValueNumber(
                        value=analyte.assay_bead_count
                    ),
                    fluorescence=TQuantityValueRelativeFluorescenceUnit(
                        value=analyte.fluorescence,
                        has_statistic_datum_role=TStatisticDatumRole.median_role,
                    ),
                )
                for analyte in analytes
            ]
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
