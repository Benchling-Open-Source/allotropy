from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._09.solution_analyzer import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_structure import (
    create_measurement_groups,
    create_metadata,
    Sample,
    Title,
)
from allotropy.parsers.vendor_parser import VendorParser


class RocheCedexBiohtParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Roche Cedex BioHT"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = RocheCedexBiohtReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = RocheCedexBiohtReader(named_file_contents.contents)

        title = Title.create(reader.title_data)
        samples = Sample.create_samples(reader.samples_data)

        return Data(
            create_metadata(title, named_file_contents.original_file_path),
            measurement_groups=create_measurement_groups(samples, title),
        )
