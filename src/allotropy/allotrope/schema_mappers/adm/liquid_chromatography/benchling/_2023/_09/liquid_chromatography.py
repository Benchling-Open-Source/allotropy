from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatogramDataCube,
    ChromatographyColumnDocument,
    DataProcessingAggregateDocument,
    DataSystemDocument,
    DerivedColumnPressureDataCube,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    FractionAggregateDocument,
    FractionDocumentItem,
    InjectionDocument,
    LiquidChromatographyAggregateDocument,
    LiquidChromatographyDocumentItem,
    LogAggregateDocument,
    LogDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    Peak as PeakDocument,
    PeakList,
    PostColumnPressureDataCube,
    PreColumnPressureDataCube,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SampleFlowRateDataCube,
    SamplePressureDataCube,
    SolventConcentrationDataCube,
    SystemFlowRateDataCube,
    SystemPressureDataCube,
    TemperatureProfileDataCube,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCentimeter,
    TQuantityValueCubicMillimeter,
    TQuantityValueHertz,
    TQuantityValueMicroliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliAbsorbanceUnitTimesSecond,
    TQuantityValueMilliliter,
    TQuantityValueMilliliterPerMinute,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValuePercent,
    TQuantityValueSecondTime,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDatacube
from allotropy.allotrope.models.shared.definitions.units import SecondTime
from allotropy.allotrope.schema_mappers.data_cube import (
    DataCube,
    get_data_cube,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import quantity_or_none, quantity_or_none_from_unit


@dataclass(frozen=True)
class DeviceDocument:
    device_type: str
    device_identifier: str | None = None
    product_manufacturer: str | None = None
    model_number: str | None = None
    equipment_serial_number: str | None = None
    firmware_version: str | None = None
    device_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Metadata:
    asset_management_identifier: str
    analyst: str | None = None
    detection_type: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    file_name: str | None = None
    data_system_instance_identifier: str | None = None
    unc_path: str | None = None
    equipment_serial_number: str | None = None
    software_version: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    device_identifier: str | None = None
    firmware_version: str | None = None
    description: str | None = None
    device_documents: list[DeviceDocument] | None = None
    lc_agg_custom_info: dict[str, Any] | None = None
    data_system_custom_info: dict[str, Any] | None = None
    device_system_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Peak:
    identifier: str
    index: str | None = None
    start: float | None = None
    start_unit: str | None = None
    end: float | None = None
    end_unit: str | None = None
    area: float | None = None
    area_unit: str | None = None
    relative_area: float | None = None
    width: float | None = None
    width_unit: str | None = None
    relative_width: float | None = None
    height: float | None = None
    height_unit: str | None = None
    relative_height: float | None = None
    retention_time: float | None = None
    peak_width_at_5_percent_of_height: float | None = None
    peak_width_at_10_percent_of_height: float | None = None
    peak_width_at_baseline: float | None = None
    asymmetry_factor_measured_at_5_percent_height: float | None = None
    asymmetry_factor_measured_at_10_percent_height: float | None = None
    number_of_theoretical_plates__chromatography_: float | None = None
    written_name: str | None = None
    chromatographic_resolution: float | None = None
    chromatographic_asymmetry: float | None = None
    width_at_half_height: float | None = None
    width_at_half_height_unit: str | None = None
    peak_analyte_amount: float | None = None
    relative_peak_analyte_amount: float | None = None
    custom_info: dict[str, Any] | None = None
    relative_retention_time: float | None = None
    capacity_factor: float | None = None
    number_of_theoretical_plates_by_peak_width_at_half_height: float | None = None

    relative_corrected_peak_area: float | None = None
    peak_group: float | None = None
    baseline_value_at_start_of_peak: float | None = None
    baseline_value_at_end_of_peak: float | None = None


@dataclass(frozen=True)
class Fraction:
    index: str
    fraction_role: str | None = None
    field_type: str | None = None
    retention_time: float | None = None
    retention_volume: float | None = None


@dataclass(frozen=True)
class Log:
    index: str
    method_identifier: str | None = None
    log_entry: str | None = None
    retention_time: float | None = None
    retention_volume: float | None = None


@dataclass(frozen=True)
class DeviceControlDoc:
    device_type: str
    start_time: str | None = None
    detection_type: str | None = None
    device_identifier: str | None = None
    product_manufacturer: str | None = None
    model_number: str | None = None
    equipment_serial_number: str | None = None
    excitation_wavelength_setting: float | None = None
    detector_wavelength_setting: float | None = None
    detector_bandwidth_setting: float | None = None
    device_control_custom_info: dict[str, Any] | None = None
    firmware_version: str | None = None
    solvent_conc_data_cube: DataCube | None = None
    pre_column_pressure_data_cube: DataCube | None = None
    sample_pressure_data_cube: DataCube | None = None
    system_pressure_data_cube: DataCube | None = None
    post_column_pressure_data_cube: DataCube | None = None
    sample_flow_data_cube: DataCube | None = None
    system_flow_data_cube: DataCube | None = None
    temperature_profile_data_cube: DataCube | None = None
    detector_offset_setting: float | None = None
    detector_sampling_rate_setting: float | None = None
    electronic_absorbance_reference_bandwidth_setting: float | None = None
    electronic_absorbance_reference_wavelength_setting: float | None = None


@dataclass(frozen=True)
class ProcessedData:
    custom_info: dict[str, Any] | None = None
    data: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    sample_identifier: str

    # Injection metadata
    injection_identifier: str
    injection_time: str

    device_control_docs: list[DeviceControlDoc]

    # Optional metadata
    processed_data_identifier: str | None = None
    measurement_time: str | None = None
    sample_role_type: str | None = None
    written_name: str | None = None
    chromatography_serial_num: str | None = None
    chromatography_part_num: str | None = None
    column_inner_diameter: float | None = None
    chromatography_chemistry_type: str | None = None
    chromatography_particle_size: float | None = None
    column_product_manufacturer: str | None = None
    chromatography_length: float | None = None
    batch_identifier: str | None = None
    void_volume: float | None = None
    flow_rate: float | None = None
    description: str | None = None
    location_identifier: str | None = None
    well_location_identifier: str | None = None
    observation: str | None = None
    injection_volume_setting: float | None = None
    autosampler_injection_volume_setting: float | None = None

    # Measurement data cubes
    chromatogram_data_cube: DataCube | None = None
    processed_data_chromatogram_data_cube: DataCube | None = None
    derived_column_pressure_data_cube: DataCube | None = None

    peaks: list[Peak] | None = None
    processed_data: list[ProcessedData] | None = None

    sample_custom_info: dict[str, Any] | None = None
    injection_custom_info: dict[str, Any] | None = None
    column_custom_info: dict[str, Any] | None = None
    measurement_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    fractions: list[Fraction] | None = None
    logs: list[Log] | None = None
    measurement_aggregate_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/liquid-chromatography/BENCHLING/2023/09/liquid-chromatography.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            liquid_chromatography_aggregate_document=add_custom_information_document(
                LiquidChromatographyAggregateDocument(
                    liquid_chromatography_document=[
                        self._get_technique_document(group, data.metadata)
                        for group in data.measurement_groups
                    ],
                    device_system_document=add_custom_information_document(
                        DeviceSystemDocument(
                            asset_management_identifier=data.metadata.asset_management_identifier,
                            product_manufacturer=data.metadata.product_manufacturer,
                            device_identifier=data.metadata.device_identifier,
                            firmware_version=data.metadata.firmware_version,
                            brand_name=data.metadata.brand_name,
                            model_number=data.metadata.model_number,
                            device_document=(
                                [
                                    add_custom_information_document(
                                        DeviceDocumentItem(
                                            device_type=doc.device_type,
                                            device_identifier=doc.device_identifier,
                                            product_manufacturer=doc.product_manufacturer,
                                            model_number=doc.model_number,
                                            equipment_serial_number=doc.equipment_serial_number,
                                            firmware_version=doc.firmware_version,
                                        ),
                                        custom_info_doc=doc.device_custom_info,
                                    )
                                    for doc in data.metadata.device_documents
                                ]
                                if data.metadata.device_documents
                                else None
                            ),
                        ),
                        data.metadata.device_system_custom_info,
                    ),
                    data_system_document=add_custom_information_document(
                        DataSystemDocument(
                            file_name=data.metadata.file_name,
                            data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                            UNC_path=data.metadata.unc_path,
                            software_name=data.metadata.software_name,
                            software_version=data.metadata.software_version,
                            ASM_converter_name=self.converter_name,
                            ASM_converter_version=ASM_CONVERTER_VERSION,
                        ),
                        data.metadata.data_system_custom_info,
                    ),
                ),
                data.metadata.lc_agg_custom_info,
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, group: MeasurementGroup, metadata: Metadata
    ) -> LiquidChromatographyDocumentItem:
        return LiquidChromatographyDocumentItem(
            analyst=metadata.analyst,
            measurement_aggregate_document=add_custom_information_document(
                MeasurementAggregateDocument(
                    measurement_document=[
                        self._get_measurement_document_item(measurement)
                        for measurement in group.measurements
                    ],
                    fraction_aggregate_document=self._get_fraction_aggregate_document(
                        group.fractions
                    ),
                    log_aggregate_document=self._get_log_aggregate_document(group.logs),
                ),
                custom_info_doc=group.measurement_aggregate_custom_info,
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        if len(measurement.device_control_docs) < 1:
            msg = "Expected at least one device control document in measurement."
            raise AllotropeConversionError(msg)

        return add_custom_information_document(
            MeasurementDocument(
                measurement_identifier=measurement.measurement_identifier,
                measurement_time=self.get_date_time(measurement.measurement_time)
                if measurement.measurement_time is not None
                else None,
                chromatography_column_document=self._get_chromatography_column_document(
                    measurement
                ),
                sample_document=self._get_sample_document(measurement),
                injection_document=(
                    self._get_injection_document(measurement)
                    if measurement.injection_identifier
                    else None
                ),
                processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                    measurement
                ),
                device_control_aggregate_document=DeviceControlAggregateDocument(
                    device_control_document=[
                        self._get_device_control_document(device_control_doc)
                        for device_control_doc in measurement.device_control_docs
                    ]
                ),
                chromatogram_data_cube=(
                    get_data_cube(
                        measurement.chromatogram_data_cube,
                        ChromatogramDataCube,
                    )
                ),
            ),
            measurement.measurement_custom_info,
        )

    def _get_chromatography_column_document(
        self, measurement: Measurement
    ) -> ChromatographyColumnDocument:
        return add_custom_information_document(
            ChromatographyColumnDocument(
                chromatography_column_serial_number=measurement.chromatography_serial_num,
                chromatography_column_chemistry_type=measurement.chromatography_chemistry_type,
                column_inner_diameter=quantity_or_none(
                    TQuantityValueMillimeter,
                    measurement.column_inner_diameter,
                ),
                chromatography_column_part_number=measurement.chromatography_part_num,
                chromatography_column_particle_size=quantity_or_none(
                    TQuantityValueMicrometer, measurement.chromatography_particle_size
                ),
                chromatography_column_length=quantity_or_none(
                    TQuantityValueCentimeter, measurement.chromatography_length
                ),
                product_manufacturer=measurement.column_product_manufacturer,
                void_volume=quantity_or_none(
                    TQuantityValueMilliliter, measurement.void_volume
                ),
            ),
            custom_info_doc=measurement.column_custom_info,
        )

    def _get_injection_document(self, measurement: Measurement) -> InjectionDocument:
        return add_custom_information_document(
            InjectionDocument(
                injection_identifier=measurement.injection_identifier,
                injection_time=self.get_date_time(measurement.injection_time),
                autosampler_injection_volume_setting__chromatography_=quantity_or_none(
                    TQuantityValueCubicMillimeter,
                    measurement.autosampler_injection_volume_setting,
                ),
                injection_volume_setting=quantity_or_none(
                    TQuantityValueMicroliter, measurement.injection_volume_setting
                ),
            ),
            measurement.injection_custom_info,
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:

        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
                description=measurement.description,
                sample_role_type=measurement.sample_role_type,
                written_name=measurement.written_name,
                flow_rate=quantity_or_none(
                    TQuantityValueMilliliterPerMinute, measurement.flow_rate
                ),
                location_identifier=measurement.location_identifier,
                well_location_identifier=measurement.well_location_identifier,
                observation=measurement.observation,
            ),
            measurement.sample_custom_info,
        )

    def _get_peak_document(self, peak: Peak) -> PeakDocument:
        return add_custom_information_document(
            PeakDocument(
                identifier=peak.identifier,
                peak_index=peak.index,
                peak_start=quantity_or_none_from_unit(peak.start_unit, peak.start),  # type: ignore[arg-type]
                peak_end=quantity_or_none_from_unit(peak.end_unit, peak.end),  # type: ignore[arg-type]
                peak_area=quantity_or_none_from_unit(peak.area_unit, peak.area),
                peak_width=quantity_or_none_from_unit(peak.width_unit, peak.width),  # type: ignore[arg-type]
                peak_height=quantity_or_none_from_unit(peak.height_unit, peak.height),
                relative_peak_area=quantity_or_none(
                    TQuantityValuePercent, peak.relative_area
                ),
                relative_peak_height=quantity_or_none(
                    TQuantityValuePercent, peak.relative_height
                ),
                retention_time=quantity_or_none(
                    TQuantityValueSecondTime, peak.retention_time
                ),
                chromatographic_peak_resolution=quantity_or_none(
                    TQuantityValueUnitless, peak.chromatographic_resolution
                ),
                chromatographic_peak_asymmetry_factor=quantity_or_none(
                    TQuantityValueUnitless, peak.chromatographic_asymmetry
                ),
                peak_width_at_half_height=quantity_or_none_from_unit(  # type: ignore[arg-type]
                    peak.width_at_half_height_unit or SecondTime.unit,
                    peak.width_at_half_height,
                ),
                relative_retention_time=quantity_or_none(
                    TQuantityValuePercent, peak.relative_retention_time
                ),
                capacity_factor__chromatography_=quantity_or_none(
                    TQuantityValueUnitless, peak.capacity_factor
                ),
                number_of_theoretical_plates_by_peak_width_at_half_height=quantity_or_none(
                    TQuantityValueUnitless,
                    peak.number_of_theoretical_plates_by_peak_width_at_half_height,
                ),
                peak_width_at_5___of_height=quantity_or_none(
                    TQuantityValueSecondTime, peak.peak_width_at_5_percent_of_height
                ),
                peak_width_at_10___of_height=quantity_or_none(
                    TQuantityValueSecondTime, peak.peak_width_at_10_percent_of_height
                ),
                peak_width_at_baseline=quantity_or_none(
                    TQuantityValueSecondTime, peak.peak_width_at_baseline
                ),
                asymmetry_factor_measured_at_5___height=quantity_or_none(
                    TQuantityValueUnitless,
                    peak.asymmetry_factor_measured_at_5_percent_height,
                ),
                asymmetry_factor_measured_at_10___height=quantity_or_none(
                    TQuantityValueUnitless,
                    peak.asymmetry_factor_measured_at_10_percent_height,
                ),
                number_of_theoretical_plates__chromatography_=quantity_or_none(
                    TQuantityValueUnitless,
                    peak.number_of_theoretical_plates__chromatography_,
                ),
                written_name=peak.written_name,
                peak_analyte_amount=quantity_or_none(
                    TQuantityValueUnitless, peak.peak_analyte_amount
                ),
                relative_corrected_peak_area=quantity_or_none(
                    TQuantityValuePercent, peak.relative_corrected_peak_area
                ),
                peak_group=quantity_or_none(
                    TQuantityValueMilliAbsorbanceUnitTimesSecond, peak.peak_group
                ),
                baseline_value_at_start_of_peak=quantity_or_none(
                    TQuantityValueSecondTime, peak.baseline_value_at_start_of_peak
                ),
                baseline_value_at_end_of_peak=quantity_or_none(
                    TQuantityValueSecondTime, peak.baseline_value_at_end_of_peak
                ),
                relative_peak_analyte_amount=quantity_or_none(
                    TQuantityValuePercent, peak.relative_peak_analyte_amount
                ),
            ),
            peak.custom_info,
        )

    def _get_processed_data_aggregate_document(
        self, measurement: Measurement
    ) -> ProcessedDataAggregateDocument | None:
        if not (
            measurement.processed_data_chromatogram_data_cube
            or measurement.derived_column_pressure_data_cube
            or measurement.peaks
        ):
            return None

        def get_data_processing_documents(pdd: ProcessedData) -> list[dict[str, Any]]:
            if not pdd.data:
                return []
            return pdd.data

        def build_peak_list() -> PeakList | None:
            if not measurement.peaks:
                return None
            return PeakList(
                peak=[self._get_peak_document(p) for p in measurement.peaks]
            )

        def build_data_document_item(
            pdd: ProcessedData | None = None,
        ) -> ProcessedDataDocumentItem:
            data_processing = (
                DataProcessingAggregateDocument(
                    data_processing_document=get_data_processing_documents(pdd)
                )
                if pdd and get_data_processing_documents(pdd)
                else None
            )
            item = ProcessedDataDocumentItem(
                chromatogram_data_cube=get_data_cube(
                    measurement.processed_data_chromatogram_data_cube, TDatacube
                ),
                derived_column_pressure_data_cube=get_data_cube(
                    measurement.derived_column_pressure_data_cube,
                    DerivedColumnPressureDataCube,
                ),
                processed_data_identifier=measurement.processed_data_identifier,
                peak_list=build_peak_list(),
                data_processing_aggregate_document=data_processing,
            )
            return (
                add_custom_information_document(item, pdd.custom_info) if pdd else item
            )

        if measurement.processed_data:
            processed_data_documents = [
                build_data_document_item(pdd) for pdd in measurement.processed_data
            ]
        else:
            processed_data_documents = [build_data_document_item()]

        return ProcessedDataAggregateDocument(
            processed_data_document=processed_data_documents
        )

    def _get_device_control_document(
        self, device_control_doc: DeviceControlDoc
    ) -> DeviceControlDocumentItem:
        custom_info = device_control_doc.device_control_custom_info or {}

        return add_custom_information_document(
            DeviceControlDocumentItem(
                device_type=device_control_doc.device_type,
                start_time_setting=(
                    self.get_date_time(device_control_doc.start_time)
                    if device_control_doc.start_time is not None
                    else None
                ),
                device_identifier=device_control_doc.device_identifier,
                detection_type=device_control_doc.detection_type,
                product_manufacturer=device_control_doc.product_manufacturer,
                equipment_serial_number=device_control_doc.equipment_serial_number,
                model_number=device_control_doc.model_number,
                firmware_version=device_control_doc.firmware_version,
                excitation_wavelength_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    device_control_doc.excitation_wavelength_setting,
                ),
                detector_wavelength_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    device_control_doc.detector_wavelength_setting,
                ),
                detector_bandwidth_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    device_control_doc.detector_bandwidth_setting,
                ),
                solvent_concentration_data_cube=get_data_cube(
                    device_control_doc.solvent_conc_data_cube,
                    SolventConcentrationDataCube,
                ),
                pre_column_pressure_data_cube=get_data_cube(
                    device_control_doc.pre_column_pressure_data_cube,
                    PreColumnPressureDataCube,
                ),
                sample_pressure_data_cube=get_data_cube(
                    device_control_doc.sample_pressure_data_cube,
                    SamplePressureDataCube,
                ),
                system_pressure_data_cube=get_data_cube(
                    device_control_doc.system_pressure_data_cube,
                    SystemPressureDataCube,
                ),
                post_column_pressure_data_cube=get_data_cube(
                    device_control_doc.post_column_pressure_data_cube,
                    PostColumnPressureDataCube,
                ),
                sample_flow_rate_data_cube=get_data_cube(
                    device_control_doc.sample_flow_data_cube,
                    SampleFlowRateDataCube,
                ),
                system_flow_rate_data_cube=get_data_cube(
                    device_control_doc.system_flow_data_cube,
                    SystemFlowRateDataCube,
                ),
                temperature_profile_data_cube=get_data_cube(
                    device_control_doc.temperature_profile_data_cube,
                    TemperatureProfileDataCube,
                ),
                detector_offset_setting=quantity_or_none(
                    TQuantityValueUnitless, device_control_doc.detector_offset_setting
                ),
                detector_sampling_rate_setting=quantity_or_none(
                    TQuantityValueHertz,
                    device_control_doc.detector_sampling_rate_setting,
                ),
                electronic_absorbance_reference_bandwidth_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    device_control_doc.electronic_absorbance_reference_bandwidth_setting,
                ),
                electronic_absorbance_reference_wavelength_setting=quantity_or_none(
                    TQuantityValueNanometer,
                    device_control_doc.electronic_absorbance_reference_wavelength_setting,
                ),
            ),
            custom_info_doc=custom_info,
        )

    def _get_fraction_aggregate_document(
        self, fractions: list[Fraction] | None
    ) -> FractionAggregateDocument | None:
        if fractions is None:
            return None

        return FractionAggregateDocument(
            fraction_document=[
                self._get_fraction_document(fraction_doc)
                for fraction_doc in fractions or []
            ]
        )

    def _get_fraction_document(self, fraction_doc: Fraction) -> FractionDocumentItem:
        return FractionDocumentItem(
            index=fraction_doc.index,
            fraction_role=fraction_doc.fraction_role,
            field_type=fraction_doc.field_type,
            retention_time=quantity_or_none(
                TQuantityValueSecondTime, fraction_doc.retention_time
            ),
            retention_volume=quantity_or_none(
                TQuantityValueMilliliter, fraction_doc.retention_volume
            ),
        )

    def _get_log_aggregate_document(
        self, logs: list[Log] | None
    ) -> LogAggregateDocument | None:
        if logs is None:
            return None

        return LogAggregateDocument(
            log_document=[self._get_log_document(log_doc) for log_doc in logs or []]
        )

    def _get_log_document(self, log_doc: Log) -> LogDocumentItem:
        return LogDocumentItem(
            index=log_doc.index,
            method_identifier=log_doc.method_identifier,
            log_entry=log_doc.log_entry,
            retention_time=quantity_or_none(
                TQuantityValueSecondTime, log_doc.retention_time
            ),
            retention_volume=quantity_or_none(
                TQuantityValueMilliliter, log_doc.retention_volume
            ),
        )
