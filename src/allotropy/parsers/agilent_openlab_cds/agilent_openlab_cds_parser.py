"""Parser file for Agilent OpenLab CDS Adapter"""
from allotropy.allotrope.models.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_openlab_cds import constants
from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_decoder import (
    decode_data,
)
from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AgilentOpenLabCDSParser(VendorParser[Data, Model]):
    DISPLAY_NAME = constants.DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = "rslt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        structured_data = decode_data(named_file_contents.original_file_path)
        return Data(
            metadata=create_metadata(structured_data, named_file_contents),
            measurement_groups=[create_measurement_groups(structured_data)],
        )
