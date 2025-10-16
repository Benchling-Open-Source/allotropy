from dataclasses import dataclass
from enum import Enum
from typing import Any

from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    UltravioletAbsorbanceSpectrumDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbanceSpectrumDetectionDeviceControlDocumentItem,
    UltravioletAbsorbanceSpectrumDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TDatacube,
    TQuantityValue,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, get_data_cube
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.units import get_quantity_class
from allotropy.parsers.utils.values import assert_not_none, quantity_or_none


class MeasurementType(Enum):
    ULTRAVIOLET_ABSORBANCE = "ULTRAVIOLET_ABSORBANCE"
    FLUORESCENCE = "FLUORESCENCE"
    ULTRAVIOLET_ABSORBANCE_SPECTRUM = "ULTRAVIOLET_ABSORBANCE_SPECTRUM"


MeasurementDocumentItems = (
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | UltravioletAbsorbanceSpectrumDetectionMeasurementDocumentItems
)


@dataclass(frozen=True)
class ProcessedDataFeature:
    result: float | InvalidJsonFloat
    unit: str
    feature: str | None = None
    identifier: str | None = None


@dataclass(frozen=True)
class ProcessedData:
    features: list[ProcessedDataFeature]
    identifier: str | None = None


@dataclass
class Measurement:
    type_: MeasurementType
    # Measurement metadata
    identifier: str
    sample_identifier: str
    data_cube: DataCube | None = None
    location_identifier: str | None = None
    batch_identifier: str | None = None
    analyst: str | None = None
    measurement_time: str | None = None
    well_plate_identifier: str | None = None

    # Settings
    sample_volume_setting: float | None = None
    detector_wavelength_setting: JsonFloat | None = None
    excitation_wavelength_setting: str | None = None
    emission_wavelength_setting: str | None = None
    dilution_factor_setting: float | None = None
    original_sample_concentration: JsonFloat | None = None
    original_sample_concentration_unit: str | None = None
    baseline_absorbance: float | None = None
    electronic_absorbance_reference_wavelength_setting: float | None = None

    # Measurements
    absorbance: JsonFloat | None = None
    fluorescence: JsonFloat | None = None

    # Processed data
    calculated_data: list[CalculatedDocument] | None = None
    processed_data: ProcessedData | None = None

    # Custom metadata
    custom_info: dict[str, Any] | None = None
    sample_custom_info: dict[str, Any] | None = None
    device_control_custom_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    plate_well_count: float | None = None
    measurement_time: str | None = None
    experiment_type: str | None = None
    analyst: str | None = None
    container_type: str | None = None

    processed_data: ProcessedData | None = None


@dataclass(frozen=True)
class Metadata:
    device_identifier: str
    device_type: str
    model_number: str
    software_name: str | None = None
    detection_type: str | None = None
    unc_path: str | None = None
    software_version: str | None = None
    equipment_serial_number: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    container_type: ContainerType | None = None

    file_name: str | None = None
    data_system_instance_id: str | None = None

    analyst: str | None = None
    measurement_time: str | None = None


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]
    calculated_data: list[CalculatedDocument] | None = None


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=data.metadata.device_identifier,
                    model_number=data.metadata.model_number,
                    brand_name=data.metadata.brand_name,
                    product_manufacturer=data.metadata.product_manufacturer,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    UNC_path=data.metadata.unc_path,
                    ASM_converter_name=self.converter_name,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                ),
                spectrophotometry_document=[
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
    ) -> SpectrophotometryDocumentItem:
        return SpectrophotometryDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self.get_date_time(
                    assert_not_none(measurement_group.measurement_time)
                ),
                experiment_type=measurement_group.experiment_type,
                container_type=metadata.container_type,
                measurement_document=[
                    self._get_measurement_document_item(measurement, metadata)
                    for measurement in measurement_group.measurements
                ],
            ),
        )

    def _get_measurement_document_item(
        self, measurement: Measurement, metadata: Metadata
    ) -> MeasurementDocumentItems:
        # TODO(switch-statement): use switch statement once Benchling can use 3.10 syntax
        if measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE:
            return self._get_ultraviolet_absorbance_measurement_document(
                measurement, metadata
            )
        elif measurement.type_ == MeasurementType.FLUORESCENCE:
            return self._get_fluorescence_measurement_document(measurement, metadata)
        elif measurement.type_ == MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM:
            return self._get_ultraviolet_absorbance_spectrum_measurement_document(
                measurement, metadata
            )
        else:
            msg = f"Invalid measurement type: {measurement.type_}"
            raise AllotropyParserError(msg)

    def _get_ultraviolet_absorbance_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> UltravioletAbsorbancePointDetectionMeasurementDocumentItems:
        doc = UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                            device_type=metadata.device_type,
                            detection_type=metadata.detection_type,
                            detector_wavelength_setting=quantity_or_none(
                                TQuantityValueNanometer,
                                measurement.detector_wavelength_setting,
                            ),
                            electronic_absorbance_reference_bandwidth_setting=quantity_or_none(
                                TQuantityValueNanometer,
                                measurement.electronic_absorbance_reference_wavelength_setting,
                            ),
                        ),
                        self._get_device_control_custom_document(measurement),
                    )
                ]
            ),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=assert_not_none(measurement.absorbance)  # type: ignore[arg-type]
            ),
            calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                measurement.calculated_data
            ),
        )
        custom_info_doc = (measurement.custom_info or {}) | {
            "baseline absorbance": quantity_or_none(
                TQuantityValueMilliAbsorbanceUnit,
                measurement.baseline_absorbance,
            ),
        }
        return add_custom_information_document(doc, custom_info_doc)

    def _get_ultraviolet_absorbance_spectrum_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> UltravioletAbsorbanceSpectrumDetectionMeasurementDocumentItems:
        doc = UltravioletAbsorbanceSpectrumDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=UltravioletAbsorbanceSpectrumDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        UltravioletAbsorbanceSpectrumDetectionDeviceControlDocumentItem(
                            device_type=metadata.device_type,
                            detection_type=metadata.detection_type,
                        ),
                        self._get_device_control_custom_document(measurement),
                    )
                ]
            ),
            absorption_spectrum_data_cube=assert_not_none(
                get_data_cube(measurement.data_cube, TDatacube),
                msg="Parser must provide absorption spectrum data cube",
            ),
        )
        return add_custom_information_document(doc, measurement.custom_info)

    def _get_fluorescence_measurement_document(
        self, measurement: Measurement, metadata: Metadata
    ) -> FluorescencePointDetectionMeasurementDocumentItems:
        doc = FluorescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=measurement.identifier,
            sample_document=self._get_sample_document(measurement),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                measurement.processed_data
            ),
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    add_custom_information_document(
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type=metadata.device_type,
                            detector_wavelength_setting=quantity_or_none(
                                TQuantityValueNanometer,
                                measurement.detector_wavelength_setting,
                            ),
                        ),
                        self._get_device_control_custom_document(measurement),
                    )
                ]
            ),
            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                value=assert_not_none(measurement.fluorescence)  # type: ignore[arg-type]
            ),
        )
        return add_custom_information_document(doc, measurement.custom_info)

    def _get_device_control_custom_document(
        self, measurement: Measurement
    ) -> dict[str, Any]:
        # TODO(ASM gaps): we believe these values should be introduced to ASM.
        custom_info = {
            "sample volume setting": quantity_or_none(
                TQuantityValueMicroliter, measurement.sample_volume_setting
            ),
            "excitation setting": measurement.excitation_wavelength_setting,
            "emission setting": measurement.emission_wavelength_setting,
            "dilution factor": quantity_or_none(
                TQuantityValueUnitless, measurement.dilution_factor_setting
            ),
        }
        return (measurement.device_control_custom_info or {}) | custom_info

    def _get_sample_document(self, measurement: Measurement) -> SampleDocument:
        # TODO(ASM gaps): we believe these values should be introduced to ASM.
        custom_info_doc = {
            "original sample concentration": quantity_or_none(
                get_quantity_class(measurement.original_sample_concentration_unit)
                or TQuantityValueUnitless,
                measurement.original_sample_concentration,
            )
        }
        # TODO: this is a temporary work around until we implement the new REC custom info doc logic, at which
        # time we will detect and convert timestamps generically.
        if (
            measurement.sample_custom_info
            and "last read standards" in measurement.sample_custom_info
        ):
            measurement.sample_custom_info["last read standards"] = self.get_date_time(
                measurement.sample_custom_info["last read standards"]
            )

        return add_custom_information_document(
            SampleDocument(
                sample_identifier=measurement.sample_identifier,
                batch_identifier=measurement.batch_identifier,
                location_identifier=measurement.location_identifier,
                well_plate_identifier=measurement.well_plate_identifier,
            ),
            (measurement.sample_custom_info or {}) | custom_info_doc,
        )

    def _get_processed_data_aggregate_document(
        self, data: ProcessedData | None
    ) -> ProcessedDataAggregateDocument | None:
        if not data:
            return None

        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    # TODO(nstender): figure out how to limit possible classes from get_quantity_class for typing.
                    mass_concentration=quantity_or_none(
                        get_quantity_class(feature.unit), feature.result  # type: ignore[arg-type]
                    ),
                    processed_data_identifier=data.identifier,
                )
                for feature in data.features
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
                    calculated_result=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=assert_not_none(calculated_data_item.unit),
                    ),
                    data_source_aggregate_document=(
                        DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier=item.reference.uuid,
                                    data_source_feature=item.feature,
                                )
                                for item in calculated_data_item.data_sources
                            ]
                        )
                        if calculated_data_item.data_sources
                        else None
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
