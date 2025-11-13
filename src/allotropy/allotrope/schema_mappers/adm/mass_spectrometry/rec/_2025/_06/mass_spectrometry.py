from dataclasses import dataclass

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.mass_spectrometry.rec._2025._06.mass_spectrometry import (
    DataProcessingAggregateDocument,
    DataProcessingDocumentItem,
    DetectorControlAggregateDocument,
    DetectorControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    MassSpectrometryAggregateDocument,
    MassSpectrometryDocumentItem,
    MeasurementDocument,
    Model,
    PeakItem,
    PeakList,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SampleIntroductionDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDalton,
    TQuantityValueHertz,
    TQuantityValueMassPerCharge,
    TQuantityValueMilliliterPerMinute,
    TQuantityValuePercent,
    TQuantityValueSecondTime,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.parsers.utils.values import quantity_or_none


@dataclass(frozen=True)
class Device:
    device_type: str
    model_number: str
    product_manufacturer: str
    device_custom_info: dict[str, object] | None = None


@dataclass(frozen=True)
class DetectorControl:
    detection_type: str
    detection_duration_setting: float | None = None
    detector_relative_offset_setting: float | None = None
    detector_sampling_rate_setting: float | None = None
    m_z_maximum_setting: float | None = None
    m_z_minimum_setting: float | None = None
    polarity_setting: str | None = None


@dataclass(frozen=True)
class SampleIntroduction:
    sample_introduction_medium: str
    sample_introduction_mode_setting: str
    flow_rate_setting: float | None = None
    laser_firing_frequency_setting: float | None = None
    sample_introduction_description: str | None = None


@dataclass(frozen=True)
class Measurement:
    analyst: str
    submitter: str
    measurement_mode_setting: str

    # Optional associations
    sample_identifier: str | None = None
    detector_control: DetectorControl | None = None
    sample_introduction: SampleIntroduction | None = None

    # Optional aggregates
    processed_data_types: list[str] | None = None
    data_processing_types: list[str] | None = None


@dataclass(frozen=True)
class Peak:
    identifier: str | None = None
    m_z: float | None = None
    mass: float | None = None
    peak_area_value: float | None = None
    peak_area_unit: str | None = None
    peak_height_value: float | None = None
    peak_height_unit: str | None = None
    peak_width_value: float | None = None
    peak_width_unit: str | None = None
    relative_peak_area: float | None = None
    relative_peak_height: float | None = None
    written_name: str | None = None


@dataclass(frozen=True)
class Metadata:
    asset_management_identifier: str
    data_processing_description: str | None = None
    devices: list[Device] | None = None
    device_system_custom_info: dict[str, object] | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurements: list[Measurement]
    peaks: list[Peak] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/mass-spectrometry/REC/2025/06/mass-spectrometry.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            manifest=self.MANIFEST,
            data_processing_description=data.metadata.data_processing_description,
            mass_spectrometry_aggregate_document=MassSpectrometryAggregateDocument(
                device_system_document=self._get_device_system_document(data.metadata),
                mass_spectrometry_document=[
                    self._get_mass_spectrometry_document_item(m)
                    for m in data.measurements
                ],
            ),
            peak_list=self._get_peak_list(data.peaks),
        )

    def _get_device_system_document(self, metadata: Metadata) -> DeviceSystemDocument:
        return add_custom_information_document(
            DeviceSystemDocument(
                asset_management_identifier=metadata.asset_management_identifier,
                device_document=[
                    DeviceDocumentItem(
                        device_type=device.device_type,
                        model_number=device.model_number,
                        product_manufacturer=device.product_manufacturer,
                    )
                    for device in (metadata.devices or [])
                ]
                or None,
            ),
            metadata.device_system_custom_info,
        )

    def _get_mass_spectrometry_document_item(
        self, measurement: Measurement
    ) -> MassSpectrometryDocumentItem:
        return MassSpectrometryDocumentItem(
            analyst=measurement.analyst,
            submitter=measurement.submitter,
            sample_document=(
                SampleDocument(sample_identifier=measurement.sample_identifier)
                if measurement.sample_identifier
                else None
            ),
            sample_introduction_document=self._get_sample_introduction_document(
                measurement.sample_introduction
            ),
            measurement_document=self._get_measurement_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data_types
            ),
            data_processing_aggregate_document=self._get_data_processing_aggregate_document(
                measurement.data_processing_types
            ),
        )

    def _get_sample_introduction_document(
        self, intro: SampleIntroduction | None
    ) -> SampleIntroductionDocument | None:
        if not intro:
            return None

        return SampleIntroductionDocument(
            sample_introduction_medium=intro.sample_introduction_medium,
            sample_introduction_mode_setting=intro.sample_introduction_mode_setting,
            flow_rate_setting=quantity_or_none(
                TQuantityValueMilliliterPerMinute, intro.flow_rate_setting
            ),
            laser_firing_frequency_setting=quantity_or_none(
                TQuantityValueHertz, intro.laser_firing_frequency_setting
            ),
            sample_introduction_description=intro.sample_introduction_description,
        )

    def _get_measurement_document(
        self, measurement: Measurement
    ) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_mode_setting=measurement.measurement_mode_setting,
            detector_control_aggregate_document=self._get_detector_control_aggregate_document(
                measurement.detector_control
            ),
        )

    def _get_detector_control_aggregate_document(
        self, control: DetectorControl | None
    ) -> DetectorControlAggregateDocument | None:
        if not control:
            return None
        return DetectorControlAggregateDocument(
            detector_control_document=[
                DetectorControlDocumentItem(
                    detection_type=control.detection_type,
                    detection_duration_setting=quantity_or_none(
                        TQuantityValueSecondTime, control.detection_duration_setting
                    ),
                    detector_relative_offset_setting=quantity_or_none(
                        TQuantityValueSecondTime,
                        control.detector_relative_offset_setting,
                    ),
                    detector_sampling_rate_setting=quantity_or_none(
                        TQuantityValueHertz, control.detector_sampling_rate_setting
                    ),
                    m_z_maximum_setting=quantity_or_none(
                        TQuantityValueMassPerCharge, control.m_z_maximum_setting
                    ),
                    m_z_minimum_setting=quantity_or_none(
                        TQuantityValueMassPerCharge, control.m_z_minimum_setting
                    ),
                    polarity_setting=control.polarity_setting,
                )
            ]
        )

    def _get_processed_data_aggregate_document(
        self, types: list[str] | None
    ) -> ProcessedDataAggregateDocument | None:
        if not types:
            return None
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(data_format_specification_type=t)
                for t in types
            ]
        )

    def _get_data_processing_aggregate_document(
        self, types: list[str] | None
    ) -> DataProcessingAggregateDocument | None:
        if not types:
            return None
        return DataProcessingAggregateDocument(
            data_processing_document=[
                DataProcessingDocumentItem(data_processing_type=t) for t in types
            ]
        )

    def _get_peak_list(self, peaks: list[Peak] | None) -> PeakList | None:
        if not peaks:
            return None
        return PeakList(
            peak=[self._get_peak_item(p) for p in peaks] or None,
        )

    def _get_peak_item(self, peak: Peak) -> PeakItem:
        return PeakItem(
            identifier=peak.identifier,
            m_z=quantity_or_none(TQuantityValueMassPerCharge, peak.m_z),
            mass=quantity_or_none(TQuantityValueDalton, peak.mass),
            peak_area=(
                TQuantityValue(value=peak.peak_area_value, unit=peak.peak_area_unit)
                if peak.peak_area_value is not None and peak.peak_area_unit is not None
                else None
            ),
            peak_height=(
                TQuantityValue(value=peak.peak_height_value, unit=peak.peak_height_unit)
                if peak.peak_height_value is not None
                and peak.peak_height_unit is not None
                else None
            ),
            peak_width=(
                TQuantityValue(value=peak.peak_width_value, unit=peak.peak_width_unit)
                if peak.peak_width_value is not None
                and peak.peak_width_unit is not None
                else None
            ),
            relative_peak_area=quantity_or_none(
                TQuantityValuePercent, peak.relative_peak_area
            ),
            relative_peak_height=quantity_or_none(
                TQuantityValuePercent, peak.relative_peak_height
            ),
            written_name=peak.written_name,
        )
