from __future__ import annotations

from io import BytesIO
from re import search
from zipfile import Path, ZipFile

from defusedxml import ElementTree

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


class UnicornFileHandler(ZipHandler):
    def get_system_data(self) -> ElementTree.Element:
        system_data = self.get_content_from_pattern("SystemData.zip$")
        b_stream = system_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return ElementTree.fromstring(raw_content[25:-1])

    def get_results(self) -> ElementTree.Element:
        b_stream = self.get_file_from_pattern("Result.xml$")
        return ElementTree.fromstring(b_stream.read())

    def get_instrument_config_data(self) -> ElementTree.Element:
        instrument_regex = "InstrumentConfigurationData.zip$"
        instrument_config_data = self.get_content_from_pattern(instrument_regex)
        b_stream = instrument_config_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return ElementTree.fromstring(raw_content[24:-1])
