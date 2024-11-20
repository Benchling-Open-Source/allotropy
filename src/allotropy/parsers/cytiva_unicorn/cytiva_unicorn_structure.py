from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import UnicornFileHandler


def create_metadata(handler: UnicornFileHandler) -> Metadata:
    system_data = handler.get_system_data()
    results = handler.get_results()
    instrument_config_data = handler.get_instrument_config_data()

    return Metadata(
        asset_management_id=system_data.find_attr(
            ["System", "InstrumentConfiguration"], "Description"
        ),
        product_manufacturer="Cytiva Life Sciences",
        device_id=results.find_text(["SystemName"]),
        firmware_version=instrument_config_data.find_text(["FirmwareVersion"]),
        analyst=handler.get_audit_trail_entry_user(),
    )


def create_measurement_groups(_: UnicornFileHandler) -> list[MeasurementGroup]:
    return []
