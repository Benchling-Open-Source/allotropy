from dataclasses import dataclass

from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceSystemDocument,
    LiquidChromatographyAggregateDocument,
    Model,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper


@dataclass(frozen=True)
class Metadata:
    asset_management_id: str
    product_manufacturer: str
    device_id: str
    firmware_version: str


@dataclass(frozen=True)
class Measurement:
    measurement_identifier: str


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