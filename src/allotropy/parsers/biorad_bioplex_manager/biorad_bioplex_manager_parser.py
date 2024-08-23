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
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    create_measurement_group,
    create_metadata,
    validate_xml_structure,
    WellSystemLevelMetadata,
)
from allotropy.parsers.biorad_bioplex_manager.constants import (
    DESCRIPTION_TAG,
    DOC_LOCATION_TAG,
    PLATE_DIMENSIONS_TAG,
    SAMPLES,
    TOTAL_WELLS_ATTRIB,
    WELLS_TAG,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import MapperVendorParser


class BioradBioplexParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Bio-Rad Bio-Plex Manager"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        contents = named_file_contents.contents.read()
        xml_tree = Et.ElementTree(Et.fromstring(contents))  # noqa: S314
        root_xml = xml_tree.getroot()
        validate_xml_structure(root_xml)

        for child in root_xml:
            if child.tag == SAMPLES:
                all_samples_xml = child
            elif child.tag == PLATE_DIMENSIONS_TAG:
                plate_well_count = int(child.attrib[TOTAL_WELLS_ATTRIB])
            elif child.tag == DOC_LOCATION_TAG:
                experimental_data_id = child.text
            elif child.tag == DESCRIPTION_TAG:
                experiment_type = child.text
        for child in root_xml:
            if child.tag == WELLS_TAG:
                well_system_metadata = WellSystemLevelMetadata.create(child[0])
                all_wells_xml = child

        return Data(
            create_metadata(root_xml, well_system_metadata, named_file_contents.original_file_name),
            [
                create_measurement_group(
                    samples_xml=all_samples_xml,
                    well_xml=well_xml,
                    regions_of_interest=well_system_metadata.regions_of_interest,
                    experimental_data_id=experimental_data_id,
                    experiment_type=experiment_type,
                    plate_well_count=plate_well_count,
                    analytical_method_identifier=well_system_metadata.analytical_method,
                    plate_id=well_system_metadata.plate_id,
                )
                for well_xml in all_wells_xml
            ]
        )
