from dataclasses import dataclass

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    ChromatogramDataCube,
    ChromatographyColumnDocument,
    DerivedColumnPressureDataCube,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    InjectionDocument,
    LiquidChromatographyAggregateDocument,
    LiquidChromatographyDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
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
    TQuantityValueCubicMillimeter,
    TQuantityValueMicrometer,
    TQuantityValueMillimeter,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDatacube
from allotropy.allotrope.schema_mappers.data_cube import (
    DataCube,
    get_data_cube,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper


@dataclass(frozen=True)
class Metadata:
    asset_management_id: str
    product_manufacturer: str
    device_id: str
    firmware_version: str
    analyst: str


@dataclass(frozen=True)
class ProcessedDataDoc:
    chromatogram_data_cube: DataCube | None = None
    derived_column_pressure_data_cube: DataCube | None = None


@dataclass(frozen=True)
class DeviceControlDoc:
    device_type: str
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

    # chromatography document
    chromatography_serial_num: str
    column_inner_diameter: float
    chromatography_chemistry_type: str
    chromatography_particle_size: float

    # injection document
    injection_identifier: str | None
    injection_time: str | None
    autosampler_injection_volume_setting: float | None

    # sample document
    sample_identifier: str
    batch_identifier: str

    device_control_docs: list[DeviceControlDoc]
    chromatogram_data_cube: DataCube | None = None
    processed_data_doc: ProcessedDataDoc | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/liquid-chromatography/BENCHLING/2023/09/liquid-chromatography.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest=self.MANIFEST,
            liquid_chromatography_aggregate_document=self.get_liquid_chromatography_agg_doc(
                data
            ),
        )

    def get_device_system_doc(self, data: Data) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            asset_management_identifier=data.metadata.asset_management_id,
            product_manufacturer=data.metadata.product_manufacturer,
            device_identifier=data.metadata.device_id,
            firmware_version=data.metadata.firmware_version,
        )

    def get_chromatography_col_doc(
        self, measurement: Measurement
    ) -> ChromatographyColumnDocument:
        return ChromatographyColumnDocument(
            chromatography_column_serial_number=measurement.chromatography_serial_num,
            chromatography_column_chemistry_type=measurement.chromatography_chemistry_type,
            column_inner_diameter=TQuantityValueMillimeter(
                value=measurement.column_inner_diameter,
            ),
            chromatography_column_particle_size=TQuantityValueMicrometer(
                value=measurement.chromatography_particle_size,
            ),
        )

    def get_sample_doc(self, measurement: Measurement) -> SampleDocument:
        return SampleDocument(
            sample_identifier=measurement.sample_identifier,
            batch_identifier=measurement.batch_identifier,
        )

    def get_injection_doc(self, measurement: Measurement) -> InjectionDocument | None:
        if (
            measurement.injection_identifier is None
            or measurement.injection_time is None
            or measurement.autosampler_injection_volume_setting is None
        ):
            return None

        return InjectionDocument(
            injection_identifier=measurement.injection_identifier,
            injection_time=self.get_date_time(measurement.injection_time),
            autosampler_injection_volume_setting__chromatography_=TQuantityValueCubicMillimeter(
                value=measurement.autosampler_injection_volume_setting,
            ),
        )

    def get_processed_data_agg_doc(
        self, processed_data_doc: ProcessedDataDoc
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    chromatogram_data_cube=get_data_cube(
                        processed_data_doc.chromatogram_data_cube,
                        TDatacube,
                    ),
                    derived_column_pressure_data_cube=get_data_cube(
                        processed_data_doc.derived_column_pressure_data_cube,
                        DerivedColumnPressureDataCube,
                    ),
                )
            ]
        )

    def get_device_control_doc_item(
        self, device_control_doc: DeviceControlDoc
    ) -> DeviceControlDocumentItem:
        return DeviceControlDocumentItem(
            device_type=device_control_doc.device_type,
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
        )

    def get_device_control_aggregate_document(
        self, device_control_docs: list[DeviceControlDoc]
    ) -> DeviceControlAggregateDocument:
        return DeviceControlAggregateDocument(
            device_control_document=[
                self.get_device_control_doc_item(device_control_doc)
                for device_control_doc in device_control_docs
            ]
        )

    def get_measurement_doc(self, measurement: Measurement) -> MeasurementDocument:
        return MeasurementDocument(
            measurement_identifier=measurement.measurement_identifier,
            chromatography_column_document=self.get_chromatography_col_doc(measurement),
            sample_document=self.get_sample_doc(measurement),
            injection_document=self.get_injection_doc(measurement),
            processed_data_aggregate_document=(
                self.get_processed_data_agg_doc(measurement.processed_data_doc)
                if measurement.processed_data_doc
                else None
            ),
            device_control_aggregate_document=self.get_device_control_aggregate_document(
                measurement.device_control_docs
            ),
            chromatogram_data_cube=get_data_cube(
                measurement.chromatogram_data_cube,
                ChromatogramDataCube,
            ),
        )

    def get_measurement_agg_doc(
        self, measurement_group: MeasurementGroup
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            measurement_document=[
                self.get_measurement_doc(measurement)
                for measurement in measurement_group.measurements
            ]
        )

    def get_liquid_chromatography_doc_item(
        self, metadata: Metadata, measurement_group: MeasurementGroup
    ) -> LiquidChromatographyDocumentItem:
        return LiquidChromatographyDocumentItem(
            analyst=metadata.analyst,
            measurement_aggregate_document=self.get_measurement_agg_doc(
                measurement_group
            ),
        )

    def get_liquid_chromatography_agg_doc(
        self, data: Data
    ) -> LiquidChromatographyAggregateDocument:
        return LiquidChromatographyAggregateDocument(
            liquid_chromatography_document=[
                self.get_liquid_chromatography_doc_item(
                    data.metadata, measurement_group
                )
                for measurement_group in data.measurement_groups
            ],
            device_system_document=self.get_device_system_doc(data),
        )
