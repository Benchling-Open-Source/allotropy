from __future__ import annotations

from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Metadata,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)


def get_audit_trail_entry_user(handler: UnicornZipHandler) -> str | None:
    evaluation_log = handler.get_evaluation_log()
    subelement_names = ["AuditTrail", "AuditTrailEntries"]
    if audit_trail_entries := evaluation_log.recursive_find_or_none(subelement_names):
        for element in audit_trail_entries.findall("AuditTrailEntry"):
            if operator := element.find_or_none("Operator"):
                if (name := operator.get_text_or_none()) != "System":
                    return name
    return None


def create_metadata(
    handler: UnicornZipHandler, results: StrictXmlElement, file_path: str
) -> Metadata:
    system_data = handler.get_system_data()
    instrument_config_data = handler.get_instrument_config_data()

    instrument_config = system_data.recursive_find(
        ["System", "InstrumentConfiguration"]
    )

    system_name = results.find_or_none("SystemName")
    firmware_version = instrument_config_data.find_or_none("FirmwareVersion")
    results.mark_read({"element:RunIndex", "element:RunType"})

    metadata = Metadata(
        asset_management_identifier=instrument_config.get_attr("Description"),
        product_manufacturer="Cytiva Life Sciences",
        device_identifier=system_name.get_text_or_none() if system_name else None,
        firmware_version=(
            firmware_version.get_text_or_none() if firmware_version else None
        ),
        analyst=get_audit_trail_entry_user(handler),
        file_name=Path(file_path).name,
        unc_path=file_path,
        data_system_custom_info={},
        software_version=results.get_attr("UNICORNVersion"),
        device_system_custom_info={
            "SystemTypeName": results.get_sub_text_or_none("SystemTypeName")
        },
    )

    if metadata.data_system_custom_info is not None:
        metadata.data_system_custom_info.update(results.get_unread())
    return metadata
