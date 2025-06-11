from dataclasses import dataclass

from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    CalibrationAggregateDocument,
    CalibrationDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
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
    StatisticDimensionAggregateDocument,
    StatisticDimensionDocumentItem,
    StatisticsAggregateDocument,
    StatisticsDocumentItem,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.models.shared.definitions.units import Unitless
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class StatisticDimension:
    value: float
    unit: str
    statistic_datum_role: TStatisticDatumRole


@dataclass(frozen=True)
class StatisticsDocument:
    statistical_feature: str
    statistic_dimensions: list[StatisticDimension]


@dataclass(frozen=True)
class Analyte:
    identifier: str
    name: str
    assay_bead_identifier: str
    assay_bead_count: float
    statistics: list[StatisticsDocument] | None = None
    statistic_datum_role: TStatisticDatumRole | None = None
    fluorescence: float | None = None


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


@dataclass(frozen=True)
class Measurement:
    # Measurement metadata
    identifier: str
    sample_identifier: str
    location_identifier: str
    measurement_time: str

    # Settings
    assay_bead_count: float

    analytes: list[Analyte]
    errors: list[Error] | None = None

    # Optional metadata
    description: str | None = None
    sample_role_type: SampleRoleType | None = None
    well_plate_identifier: str | None = None

    # Optional settings
    sample_volume_setting: float | None = None
    dilution_factor_setting: float | None = None
    minimum_assay_bead_count_setting: float | None = None
    detector_gain_setting: str | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float
    analyst: str | None
    analytical_method_identifier: str | None = None
    experimental_data_identifier: str | None = None
    method_version: str | None = None
    container_type: str | None = None
    experiment_type: str | None = None


@dataclass(frozen=True)
class Calibration:
    name: str
    report: str
    time: str


@dataclass(frozen=True)
class Metadata:
    file_name: str
    asm_file_identifier: str
    unc_path: str
    device_type: str
    data_system_instance_identifier: str
    model_number: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    firmware_version: str | None = None
    product_manufacturer: str | None = None

    calibrations: list[Calibration] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDocument] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/09/multi-analyte-profiling.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            multi_analyte_profiling_aggregate_document=MultiAnalyteProfilingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    product_manufacturer=data.metadata.product_manufacturer,
                    firmware_version=data.metadata.firmware_version,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    calibration_aggregate_document=self._get_calibration_aggregate_document(
                        data.metadata.calibrations
                    ),
                ),
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_file_identifier=data.metadata.asm_file_identifier,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                multi_analyte_profiling_document=[
                    self._get_technique_document(measurement_group, data.metadata)
                    for measurement_group in data.measurement_groups
                ],
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data.calculated_data
                ),
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup, metadata: Metadata
    ) -> MultiAnalyteProfilingDocumentItem:
        return MultiAnalyteProfilingDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                experiment_type=measurement_group.experiment_type,
                analytical_method_identifier=measurement_group.analytical_method_identifier,
                method_version=measurement_group.method_version,
                experimental_data_identifier=measurement_group.experimental_data_identifier,
                container_type=measurement_group.container_type,
                plate_well_count=quantity_or_none(
                    TQuantityValueNumber, measurement_group.plate_well_count
                ),
                measurement_document=[
                    self._get_measurement_document(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document(
        self, measurement: Measurement, metadata: Metadata
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
                            TQuantityValueMicroliter, measurement.sample_volume_setting
                        ),
                        dilution_factor_setting=quantity_or_none(
                            TQuantityValueUnitless, measurement.dilution_factor_setting
                        ),
                        detector_gain_setting=measurement.detector_gain_setting,
                        minimum_assay_bead_count_threshold_setting=quantity_or_none(
                            TQuantityValueNumber,
                            measurement.minimum_assay_bead_count_setting,
                        ),
                    )
                ]
            ),
            assay_bead_count=TQuantityValueNumber(value=measurement.assay_bead_count),
            analyte_aggregate_document=AnalyteAggregateDocument(
                analyte_document=[
                    AnalyteDocumentItem(
                        analyte_identifier=analyte.identifier,
                        analyte_name=analyte.name,
                        assay_bead_identifier=analyte.assay_bead_identifier,
                        assay_bead_count=TQuantityValueNumber(
                            value=analyte.assay_bead_count
                        ),
                        fluorescence=quantity_or_none(
                            TQuantityValueRelativeFluorescenceUnit,
                            analyte.fluorescence,
                            has_statistic_datum_role=analyte.statistic_datum_role,
                        ),
                        statistics_aggregate_document=(
                            StatisticsAggregateDocument(
                                statistics_document=[
                                    StatisticsDocumentItem(
                                        statistical_feature=statistic.statistical_feature,
                                        statistic_dimension_aggregate_document=StatisticDimensionAggregateDocument(
                                            statistic_dimension_document=[
                                                StatisticDimensionDocumentItem(
                                                    statistical_value=TQuantityValueModel(
                                                        value=dimension.value,
                                                        unit=dimension.unit,
                                                        has_statistic_datum_role=dimension.statistic_datum_role,
                                                    ),
                                                )
                                                for dimension in statistic.statistic_dimensions
                                            ]
                                        ),
                                    )
                                    for statistic in analyte.statistics
                                ]
                            )
                            if analyte.statistics
                            else None
                        ),
                    )
                    for analyte in measurement.analytes
                ]
            ),
            error_aggregate_document=self._get_error_aggregate_document(
                measurement.errors
            ),
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            location_identifier=measurement.location_identifier,
            description=measurement.description,
            sample_role_type=(
                measurement.sample_role_type.value
                if measurement.sample_role_type
                else None
            ),
            well_plate_identifier=measurement.well_plate_identifier,
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
        self, calculated_data_items: list[CalculatedDocument] | None
    ) -> CalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.uuid,
                    calculated_data_name=calculated_data_item.name,
                    calculation_description=calculated_data_item.description,
                    calculated_result=TQuantityValueModel(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit or Unitless.unit,
                    ),
                    data_source_aggregate_document=DataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.reference.uuid,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_sources
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
