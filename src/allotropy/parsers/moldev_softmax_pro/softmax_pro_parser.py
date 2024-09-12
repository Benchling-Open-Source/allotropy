from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import Model
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
    StructureData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class SoftmaxproParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Molecular Devices SoftMax Pro"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = StructureData.create(reader)

        return Data(
            create_metadata(named_file_contents.original_file_name),
            create_measurement_groups(data),
            create_calculated_data(data),
        )
