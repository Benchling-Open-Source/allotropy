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

    def get_chrom_1(self) -> StrictElement:
        b_stream = self.get_file_from_pattern("Chrom.1.Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content)

    def get_column_type_data(self) -> StrictElement:
        column_type_data = self.get_content_from_pattern("ColumnTypeData.zip$")
        b_stream = column_type_data.get_file_from_pattern("^Xml$")
        raw_content = b_stream.read()
        return StrictElement.create_from_bytes(raw_content[24:-1])
