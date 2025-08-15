from allotropy.allotrope.models.adm.plate_reader.rec._2025._03.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    Data,
    Mapper,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    create_metadata,
    get_processor,
)
from allotropy.parsers.agilent_gen5.constants import (
    NO_MEASUREMENTS_ERROR,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper
    UNREAD_DATA_HANDLED = True

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)
        context = reader.extract_data_context(named_file_contents.original_file_path)

        processor = get_processor(context)
        measurement_groups, calculated_data = processor.process(context)

        if not measurement_groups:
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        return Data(
            metadata=create_metadata(context.header_data),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )
