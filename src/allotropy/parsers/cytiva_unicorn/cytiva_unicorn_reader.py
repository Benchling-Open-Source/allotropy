from __future__ import annotations

from io import BytesIO
from re import search
from xml.etree import ElementTree
from zipfile import Path, ZipFile

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

from allotropy.parsers.utils.values import assert_not_none


class ZipHandler:
    def __init__(self, path: str, inner_path: str = "", data: BytesIO | None = None):
        self.path = path
        self.inner_path = inner_path
        self.zip_path = Path(path, inner_path)
        self.zip_file = ZipFile(path if data is None else data)
        self.name_list = self.zip_file.namelist()

    def get_file_path_or_none(self, pattern: str) -> str | None:
        for file_name in self.name_list:
            if search(pattern, file_name):
                return file_name
        return None

    def get_file_path(self, pattern: str) -> str:
        return assert_not_none(
            self.get_file_path_or_none(pattern),
            msg=f"Unable to find file inside {self.path} that match pattern {pattern}",
        )

    def __get_raw_content(self, inner_path: str) -> BytesIO:
        return BytesIO(self.zip_file.read(inner_path))

    def __get_content(self, inner_path: str) -> ZipHandler:
        return ZipHandler(self.path, inner_path, self.__get_raw_content(inner_path))

    def get_file_from_pattern(self, pattern: str) -> BytesIO:
        return self.__get_raw_content(self.get_file_path(pattern))

    def get_content_from_pattern(self, pattern: str) -> ZipHandler:
        return self.__get_content(self.get_file_path(pattern))


class StrictElement:
    def __init__(self, element: ElementTree.Element):
        self.element = element

    def find(self, name: str) -> StrictElement:
        return StrictElement(
            assert_not_none(
                self.element.find(name),
                msg=f"Unable to find {name} in xml file contents",
            )
        )

    def findall(self, name: str) -> list[StrictElement]:
        return [StrictElement(element) for element in self.element.findall(name)]

    def get(self, name: str) -> str:
        return assert_not_none(
            self.element.get(name),
            msg=f"Unable to find {name} in xml file contents",
        )

    def recursive_find(self, names: list[str]) -> StrictElement:
        if len(names) == 0:
            return self
        name, *sub_names = names
        return self.find(name).recursive_find(sub_names)

    def find_attr(self, names: list[str], attr: str) -> str:
        return self.recursive_find(names).get(attr)

    def find_text(self, names: list[str]) -> str:
        return str(self.recursive_find(names).element.text)


class UnicornFileHandler(ZipHandler):
    def get_system_data(self) -> StrictElement:
        system_data = self.get_content_from_pattern("SystemData.zip$")
        b_stream = system_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        element = fromstring(raw_content[25:-1])
        return StrictElement(element)

    def get_results(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("Result.xml$")
        element = fromstring(b_stream.read())
        return StrictElement(element)

    def get_instrument_config_data(self) -> StrictElement:
        instrument_regex = "InstrumentConfigurationData.zip$"
        instrument_config_data = self.get_content_from_pattern(instrument_regex)
        b_stream = instrument_config_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        element = fromstring(raw_content[24:-1])
        return StrictElement(element)

    def get_evaluation_log(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("EvaluationLog.xml$")
        element = fromstring(b_stream.read())
        return StrictElement(element)

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
        element = fromstring(b_stream.read())
        return StrictElement(element)
