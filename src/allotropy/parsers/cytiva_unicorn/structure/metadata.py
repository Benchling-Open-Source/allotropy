from __future__ import annotations

from pathlib import Path
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
    subelement_names = ["AuditTrail", "AuditTrailEntries"]
    if audit_trail_entries := element.recursive_find_or_none(subelement_names):
        for element in audit_trail_entries.findall("AuditTrailEntry"):
            if group_name := element.find_or_none("GroupName"):
                if group_name.get_text() == "EvaluationLoggingStarted":
                    return element
    return None


def get_audit_trail_entry_user(handler: UnicornZipHandler) -> str:
    evaluation_log = handler.get_evaluation_log()
    if audit_trail_entry := get_audit_trail_entry(evaluation_log):
        if log_entry := audit_trail_entry.find("LogEntry"):
            if match := search(r"User: (.+)\. ", log_entry.get_text()):
                return match.group(1)
    return "Default"


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

    return Metadata(
        asset_management_identifier=instrument_config.get_attr("Description"),
        product_manufacturer="Cytiva Life Sciences",
        device_identifier=system_name.get_text() if system_name else None,
        firmware_version=firmware_version.get_text() if firmware_version else None,
        analyst=get_audit_trail_entry_user(handler),
        file_name=Path(file_path).name,
        unc_path=file_path,
    )
