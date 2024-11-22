from dataclasses import dataclass

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceSystemDocument,
    LiquidChromatographyAggregateDocument,
    Model,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
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
class DataCubeComponent:
    type_: FieldComponentDatatype
    concept: str
    unit: str


@dataclass(frozen=True)
class DataCube:
    label: str
    structure_dimensions: list[DataCubeComponent]
    structure_measures: list[DataCubeComponent]
    dimensions: list[tuple[float, ...]]
    measures: list[tuple[float | None, ...]]


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
class ChromatographyDoc:
    chromatography_serial_num: str
    column_inner_diameter: str
    chromatography_chemistry_type: str
    chromatography_particle_size: str


@dataclass(frozen=True)
class InjectionDoc:
    injection_identifier: str
    injection_time: str
    autosampler_injection_volume_setting: str


@dataclass(frozen=True)
class SampleDoc:
    sample_identifier: str
    batch_identifier: str


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str
    data_cube: DataCube | None = None
    processed_data_doc: ProcessedDataDoc | None = None
    device_control_docs: list[DeviceControlDoc] | None = None
    chromatography_column_doc: ChromatographyDoc | None = None
    injection_doc: InjectionDoc | None = None
    sample_doc: SampleDoc | None = None


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
            liquid_chromatography_aggregate_document=self.get_liquid_chromatography_agg_doc(
                data
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def get_liquid_chromatography_agg_doc(
        self, data: Data
    ) -> LiquidChromatographyAggregateDocument:
        return LiquidChromatographyAggregateDocument(
            liquid_chromatography_document=[],
            device_system_document=self.get_device_system_doc(data),
            # processed_data_aggregate_document: ProcessedDataAggregateDocument
        )

    def get_device_system_doc(self, data: Data) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            asset_management_identifier=data.metadata.asset_management_id,
            product_manufacturer=data.metadata.product_manufacturer,
            device_identifier=data.metadata.device_id,
            firmware_version=data.metadata.firmware_version,
        )
