from re import search

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.strict_element import (
    StrictElement,
)
from allotropy.parsers.cytiva_unicorn.reader.zip_handler import (
    ZipHandler,
)


class UnicornZipHandler(ZipHandler):
    def get_system_data(self) -> StrictElement:
        system_data = self.get_content_from_pattern("SystemData.zip$")
        b_stream = system_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content[25:-1])

    def get_results(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("Result.xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content)

    def get_instrument_config_data(self) -> StrictElement:
        instrument_regex = "InstrumentConfigurationData.zip$"
        instrument_config_data = self.get_content_from_pattern(instrument_regex)
        b_stream = instrument_config_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content[24:-1])

    def get_evaluation_log(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("EvaluationLog.xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content)

    def __get_audit_trail_entry(self, element: StrictElement) -> StrictElement | None:
        audit_trail_entries = element.recursive_find(
            ["AuditTrail", "AuditTrailEntries"]
        )
        for element in audit_trail_entries.findall("AuditTrailEntry"):
            if element.find_text(["GroupName"]) == "EvaluationLoggingStarted":
                return element
        return None

    def get_audit_trail_entry_user(self) -> str:
        if audit_trail_entry := self.__get_audit_trail_entry(self.get_evaluation_log()):
            if match := search(
                r"User: (.+)\. ",
                audit_trail_entry.find_text(["LogEntry"]),
            ):
                return match.group(1)
        return "Default"

    def get_chrom_1(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("Chrom.1.Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content)

    def get_column_type_data(self) -> StrictElement:
        column_type_data = self.get_content_from_pattern("ColumnTypeData.zip$")
        b_stream = column_type_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content[24:-1])

    def filter_curve(
        self, curve_elements: list[StrictElement], pattern: str
    ) -> StrictElement:
        for element in curve_elements:
            if search(pattern, element.find_text(["Name"])):
                return element
        msg = f"Unable to find curve element with pattern {pattern}"
        raise AllotropeConversionError(msg)

    def filter_result_criteria(
        self, results: StrictElement, keyword: str
    ) -> StrictElement:
        for result_criteria in results.find("ResultSearchCriterias").findall(
            "ResultSearchCriteria"
        ):
            if result_criteria.find_text(["Keyword1"]) == keyword:
                return result_criteria
        msg = f"Unable to find result criteria with keyword 1 '{keyword}'"
        raise AllotropeConversionError(msg)
