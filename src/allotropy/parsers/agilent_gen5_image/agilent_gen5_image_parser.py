from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    get_identifiers,
    get_results_section,
    HeaderData,
)
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_structure import (
    create_metadata,
    create_results,
    ReadData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AgilentGen5ImageParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5 Image"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)

        header_data = HeaderData.create(
            reader.header_data, named_file_contents.original_file_path
        )
        read_data = ReadData.create(reader.sections["Procedure Details"])

        return Data(
            metadata=create_metadata(header_data),
            measurement_groups=create_results(
                get_results_section(reader),
                header_data,
                read_data,
                get_identifiers(reader.sections.get("Layout")),
            ),
        )
