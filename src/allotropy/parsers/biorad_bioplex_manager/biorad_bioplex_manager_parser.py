from __future__ import annotations

from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_reader import (
    BioradBioplexReader,
)
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    create_measurement_group,
    create_metadata,
    SampleMetadata,
    SystemMetadata,
    Well,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class BioradBioplexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Bio-Rad Bio-Plex Manager"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "xml"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BioradBioplexReader(named_file_contents)

        samples_dict = SampleMetadata.create_samples(reader["Samples"])
        # Only parse system-level metadata once, from the first well.
        system_metadata = SystemMetadata.create(reader["Wells"][0])

        return Data(
            create_metadata(
                reader.root, system_metadata, named_file_contents.original_file_path
            ),
            [
                create_measurement_group(
                    well,
                    samples_dict[well.name],
                    system_metadata,
                    experimental_data_id=reader["NativeDocumentLocation"].text,
                    experiment_type=reader["Description"].text,
                    plate_well_count=int(
                        reader.get_attribute("PlateDimensions", "TotalWells")
                    ),
                )
                for well in [Well.create(well_xml) for well_xml in reader["Wells"]]
            ],
        )
