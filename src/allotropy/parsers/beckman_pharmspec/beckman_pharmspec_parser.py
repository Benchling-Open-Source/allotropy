from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_reader import (
    BeckmanPharmspecReader,
)
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
    Distribution,
    Header,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class PharmSpecParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Beckman Coulter PharmSpec"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BeckmanPharmspecReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BeckmanPharmspecReader(named_file_contents)
        distributions = Distribution.create_distributions(reader.data)
        header = Header.create(reader.header)

        return Data(
            create_metadata(header, named_file_contents.original_file_path),
            create_measurement_groups(header, distributions),
            create_calculated_data(distributions),
        )
