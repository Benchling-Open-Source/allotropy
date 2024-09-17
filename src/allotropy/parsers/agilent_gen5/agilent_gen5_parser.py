from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    create_metadata,
    create_results,
    get_identifiers,
    get_temperature,
    HeaderData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import DEFAULT_EXPORT_FORMAT_ERROR
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class AgilentGen5Parser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)

        if "Results" not in reader.sections:
            raise AllotropeConversionError(DEFAULT_EXPORT_FORMAT_ERROR)

        header_data = HeaderData.create(
            reader.header_data, named_file_contents.original_file_name
        )
        read_data = ReadData.create(reader.sections["Procedure Details"])

        sample_identifiers = get_identifiers(reader.sections.get("Layout"))
        actual_temperature = get_temperature(reader.sections.get("Actual Temperature"))

        measurement_groups, calculated_data = create_results(
            reader.sections["Results"],
            header_data,
            read_data,
            sample_identifiers,
            actual_temperature,
        )

        return Data(
            metadata=create_metadata(header_data),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )
