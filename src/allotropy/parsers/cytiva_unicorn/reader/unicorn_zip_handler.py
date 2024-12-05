from __future__ import annotations

from io import BytesIO

from allotropy.parsers.cytiva_unicorn.reader.strict_xml_element import (
    StrictXmlElement,
)
from allotropy.parsers.cytiva_unicorn.reader.zip_handler import (
    ZipHandler,
)


class UnicornZipHandler(ZipHandler):
    def get_zip(self, inner_path: str) -> UnicornZipHandler:
        return UnicornZipHandler(self.get_file(inner_path))

    def get_zip_from_pattern(self, pattern: str) -> UnicornZipHandler:
        return self.get_zip(self.get_inner_path(pattern))

    @classmethod
    def create_from_path(cls, path: str) -> UnicornZipHandler:
        with open(path, "rb") as f:
            data = f.read()
        return UnicornZipHandler(data=BytesIO(data))

    def filter_xml_metadata(self, stream: BytesIO) -> BytesIO:
        data = stream.read()
        lower_symbol, upper_symbol = 32, 126

        start = 0
        for idx, element in enumerate(data):
            if lower_symbol <= int(element) <= upper_symbol:
                start = idx
                break

        end = len(data)
        for idx, element in enumerate(reversed(data)):
            if lower_symbol <= int(element) <= upper_symbol:
                end -= idx
                break

        return BytesIO(data[start:end])

    def get_system_data(self) -> StrictXmlElement:
        system_data = self.get_zip_from_pattern("SystemData.zip$")
        b_stream = system_data.get_file_from_pattern("^Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_results(self) -> StrictXmlElement:
        b_stream = self.get_file_from_pattern("Result.xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_instrument_config_data(self) -> StrictXmlElement:
        instrument_regex = "InstrumentConfigurationData.zip$"
        instrument_config_data = self.get_zip_from_pattern(instrument_regex)
        b_stream = instrument_config_data.get_file_from_pattern("^Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_evaluation_log(self) -> StrictXmlElement:
        b_stream = self.get_file_from_pattern("EvaluationLog.xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_chrom_1(self) -> StrictXmlElement:
        b_stream = self.get_file_from_pattern("Chrom.1.Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_column_type_data(self) -> StrictXmlElement:
        column_type_data = self.get_zip_from_pattern("ColumnTypeData.zip$")
        b_stream = column_type_data.get_file_from_pattern("^Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)
