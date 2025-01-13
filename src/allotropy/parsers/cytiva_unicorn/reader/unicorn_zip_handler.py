from __future__ import annotations

from io import BytesIO

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.reader.zip_handler import (
    ZipHandler,
)
from allotropy.parsers.utils.strict_xml_element import (
    StrictXmlElement,
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
        start = -1
        for idx, element in enumerate(data):
            if int(element) == 60:  # 60 == '<' ASCII char
                start = idx
                break

        end = -1
        for idx, element in enumerate(reversed(data)):
            if int(element) == 62:  # 62 == '>' ASCII char
                end = len(data) - idx
                break

        if start == -1 or end == -1:
            msg = "Unable to extract XML from file."
            raise AllotropeConversionError(msg)

        return BytesIO(data[start:end])

    def get_system_data(self) -> StrictXmlElement:
        system_data = self.get_zip_from_pattern("SystemData(.zip)?$")
        b_stream = system_data.get_file_from_pattern("^Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_results(self) -> StrictXmlElement:
        b_stream = self.get_file_from_pattern("Result.xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)

    def get_instrument_config_data(self) -> StrictXmlElement:
        instrument_regex = "InstrumentConfigurationData(.zip)?$"
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
        column_type_data = self.get_zip_from_pattern("ColumnTypeData(.zip)?$")
        b_stream = column_type_data.get_file_from_pattern("^Xml$")
        raw_content = self.filter_xml_metadata(b_stream).read()
        return StrictXmlElement.create_from_bytes(raw_content)
