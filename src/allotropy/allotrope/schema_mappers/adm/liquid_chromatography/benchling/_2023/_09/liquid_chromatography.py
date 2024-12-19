from dataclasses import dataclass
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatogramDataCube,
    ChromatographyColumnDocument,
    DataSystemDocument,
    DerivedColumnPressureDataCube,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    InjectionDocument,
    LiquidChromatographyAggregateDocument,
    LiquidChromatographyDocumentItem,
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
    TQuantityValueMicrometer,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValuePercent,
    TQuantityValueSecondTime,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDatacube
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
    device_identifier: str
    product_manufacturer: str
    model_number: str
    equipment_serial_number: str
    firmware_version: str
    device_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Metadata:
    asset_management_identifier: str
    analyst: str
    detection_type: str | None = None
    model_number: str | None = None
    software_name: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    equipment_serial_number: str | None = None
    software_version: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    device_identifier: str | None = None
    firmware_version: str | None = None
    description: str | None = None
    device_document: list[DeviceDocument] | None = None


@dataclass(frozen=True)
class Peak:
    identifier: str
    start: float
    start_unit: str
    end: float
    end_unit: str
    area: float | None = None
    area_unit: str | None = None
    relative_area: float | None = None
    width: float | None = None
    relative_width: float | None = None
    height: float | None = None
    height_unit: str | None = None
    relative_height: float | None = None
    retention_time: float | None = None
    chromatographic_peak_resolution: float | None = None
    peak_width_at_half_height: float | None = None
    asymmetry_factor_measured_at_10___heigh: float | None = None
    peak_width_at_5___of_height: float | None = None
    peak_width_at_10___of_height: float | None = None
    peak_width_at_baseline: float | None = None
    asymmetry_factor_measured_at_10___height: float | None = None
    number_of_theoretical_plates__chromatography_: float | None = None
    written_name: str | None = None


@dataclass(frozen=True)
class DeviceControlDoc:
    device_type: str
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


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    sample_identifier: str

    # Injection metadata
    injection_identifier: str
    injection_time: str
    autosampler_injection_volume_setting: float

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
    sample_custom_info: dict[str, Any] | None = None
    injection_custom_info: dict[str, Any] | None = None
    column_custom_info: dict[str, Any] | None = None

    # Measurement data cubes
    chromatogram_data_cube: DataCube | None = None
    processed_data_chromatogram_data_cube: DataCube | None = None
    derived_column_pressure_data_cube: DataCube | None = None

    peaks: list[Peak] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    measurement_aggregate_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/liquid-chromatography/BENCHLING/2023/09/liquid-chromatography.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            liquid_chromatography_aggregate_document=LiquidChromatographyAggregateDocument(
                liquid_chromatography_document=[
                    self._get_technique_document(group, data.metadata)
                    for group in data.measurement_groups
                ],
                device_system_document=DeviceSystemDocument(
                    asset_management_identifier=data.metadata.asset_management_identifier,
                    product_manufacturer=data.metadata.product_manufacturer,
                    device_identifier=data.metadata.device_identifier,
                    firmware_version=data.metadata.firmware_version,
                    device_document=(
                        [
                            add_custom_information_document(
                                DeviceDocumentItem(
                                    device_type=device_document_item.device_type,
                                    device_identifier=device_document_item.device_identifier,
                                    product_manufacturer=device_document_item.product_manufacturer,
                                    model_number=device_document_item.model_number,
                                    equipment_serial_number=device_document_item.equipment_serial_number,
                                    firmware_version=device_document_item.firmware_version,
                                ),
                                custom_info_doc=device_document_item.device_custom_info,
                            )
                            for device_document_item in data.metadata.device_document
                        ]
                        if data.metadata.device_document is not None
                        else None
                    ),
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
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
                    ]
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

        return MeasurementDocument(
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
            ),
            custom_info_doc=measurement.column_custom_info,
        )

    def _get_injection_document(self, measurement: Measurement) -> InjectionDocument:
        return add_custom_information_document(
            InjectionDocument(
                injection_identifier=measurement.injection_identifier,
                injection_time=self.get_date_time(measurement.injection_time),
                autosampler_injection_volume_setting__chromatography_=TQuantityValueCubicMillimeter(
                    value=measurement.autosampler_injection_volume_setting,
                ),
            ),
            custom_info_doc=measurement.injection_custom_info,
        )

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
                sample_role_type=measurement.sample_role_type,
                written_name=measurement.written_name,
            ),
            custom_info_doc=measurement.sample_custom_info,
        )

    def _get_peak_document(self, peak: Peak) -> PeakDocument:
        return PeakDocument(
            identifier=peak.identifier,
            peak_start=quantity_or_none_from_unit(peak.start_unit, peak.start),  # type: ignore[arg-type]
            peak_end=quantity_or_none_from_unit(peak.end_unit, peak.end),  # type: ignore[arg-type]
            peak_area=quantity_or_none_from_unit(peak.area_unit, peak.area),
            peak_width=quantity_or_none(TQuantityValueSecondTime, peak.width),
            peak_height=quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit, peak.height
            ),
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
                TQuantityValueUnitless, peak.chromatographic_peak_resolution
            ),
            peak_width_at_half_height=quantity_or_none(
                TQuantityValueSecondTime, peak.peak_width_at_half_height
            ),
            asymmetry_factor_measured_at_10___height=quantity_or_none(
                TQuantityValueUnitless, peak.asymmetry_factor_measured_at_10___height
            ),
            peak_width_at_5___of_height=quantity_or_none(
                TQuantityValueSecondTime, peak.peak_width_at_5___of_height
            ),
            peak_width_at_10___of_height=quantity_or_none(
                TQuantityValueSecondTime, peak.peak_width_at_10___of_height
            ),
            peak_width_at_baseline=quantity_or_none(
                TQuantityValueSecondTime, peak.peak_width_at_baseline
            ),
            number_of_theoretical_plates__chromatography_=quantity_or_none(
                TQuantityValueUnitless,
                peak.number_of_theoretical_plates__chromatography_,
            ),
            written_name=peak.written_name,
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
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    chromatogram_data_cube=get_data_cube(
                        measurement.processed_data_chromatogram_data_cube,
                        TDatacube,
                    ),
                    derived_column_pressure_data_cube=get_data_cube(
                        measurement.derived_column_pressure_data_cube,
                        DerivedColumnPressureDataCube,
                    ),
                    processed_data_identifier=measurement.processed_data_identifier,
                    peak_list=PeakList(
                        peak=[
                            self._get_peak_document(peak) for peak in measurement.peaks
                        ]
                    )
                    if measurement.peaks
                    else None,
                )
            ]
        )

    def _get_device_control_document(
        self, device_control_doc: DeviceControlDoc
    ) -> DeviceControlDocumentItem:
        return add_custom_information_document(
            DeviceControlDocumentItem(
                device_type=device_control_doc.device_type,
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
            ),
            custom_info_doc=device_control_doc.device_control_custom_info,
        )
