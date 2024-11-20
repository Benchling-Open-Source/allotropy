from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import UnicornFileHandler


def create_metadata(_: UnicornFileHandler) -> Metadata:
    return Metadata(
        asset_management_id="",
        product_manufacturer="Cytiva Life Sciences",
        device_id="",
        firmware_version="",
    )


def create_measurement_groups(_: UnicornFileHandler) -> list[MeasurementGroup]:
    return []
