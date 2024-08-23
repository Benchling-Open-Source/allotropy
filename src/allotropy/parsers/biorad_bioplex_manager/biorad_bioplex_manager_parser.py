from __future__ import annotations

import xml.etree.ElementTree as Et

from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
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
from allotropy.parsers.vendor_parser import MapperVendorParser


class BioradBioplexParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Bio-Rad Bio-Plex Manager"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = BioradBioplexReader(named_file_contents)

        samples_dict = SampleMetadata.create_samples(reader.get("Samples"))
        system_metadata = SystemMetadata.create(reader.get("Wells")[0])
        wells = [Well.create(well_xml) for well_xml in reader.get("Wells")]

        return Data(
            create_metadata(reader.root, system_metadata, named_file_contents.original_file_name),
            [
                create_measurement_group(
                    well,
                    samples_dict[well.name],
                    system_metadata,
                    experimental_data_id=reader.get("NativeDocumentLocation").text,
                    experiment_type=reader.get("Description").text,
                    plate_well_count=int(reader.get("PlateDimensions").attrib["TotalWells"]),
                )
                for well in wells
            ]
        )
