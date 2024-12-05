from __future__ import annotations

from re import search

from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Metadata,
)
from allotropy.parsers.cytiva_unicorn.reader.unicorn_zip_handler import (
    UnicornZipHandler,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
)


def get_audit_trail_entry(element: StrictXmlElement) -> StrictXmlElement | None:
    audit_trail_entries = element.recursive_find(["AuditTrail", "AuditTrailEntries"])
    for element in audit_trail_entries.findall("AuditTrailEntry"):
        if element.find("GroupName").get_text() == "EvaluationLoggingStarted":
            return element
    return None


def get_audit_trail_entry_user(handler: UnicornZipHandler) -> str:
    evaluation_log = handler.get_evaluation_log()
    if audit_trail_entry := get_audit_trail_entry(evaluation_log):
        if match := search(
            r"User: (.+)\. ",
            audit_trail_entry.find("LogEntry").get_text(),
        ):
            return match.group(1)
    return "Default"


def create_metadata(handler: UnicornZipHandler, results: StrictXmlElement) -> Metadata:
    system_data = handler.get_system_data()
    instrument_config_data = handler.get_instrument_config_data()

    instrument_config = system_data.recursive_find(
        ["System", "InstrumentConfiguration"]
    )

    return Metadata(
        asset_management_id=instrument_config.get_attr("Description"),
        product_manufacturer="Cytiva Life Sciences",
        device_id=results.find("SystemName").get_text(),
        firmware_version=instrument_config_data.find("FirmwareVersion").get_text(),
        analyst=get_audit_trail_entry_user(handler),
    )
