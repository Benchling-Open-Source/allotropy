from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.light_obscuration.benchling._2023._12.light_obscuration import (
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
    DISPLAY_NAME = "Beckman PharmSpec"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = BeckmanPharmspecReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BeckmanPharmspecReader(named_file_contents)
        distributions = Distribution.create_distributions(reader.data)
        header = Header.create(reader.header)

        return Data(
            create_metadata(header, named_file_contents.original_file_name),
            create_measurement_groups(header, distributions),
            create_calculated_data(distributions),
        )
