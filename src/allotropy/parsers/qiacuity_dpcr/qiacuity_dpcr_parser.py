from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
    MeasurementGroup,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_reader import QiacuitydPCRReader
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_structure import (
    create_measurements,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class QiacuitydPCRParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Qiacuity dPCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = QiacuitydPCRReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = QiacuitydPCRReader(named_file_contents)
        return Data(
            create_metadata(named_file_contents.original_file_path),
            measurement_groups=[
                MeasurementGroup(
                    measurements=map_rows(reader.well_data, create_measurements),
                    # TODO: Hardcoded plate well count to 0 since it's a required field
                    #  ASM will be modified to optional in future version
                    plate_well_count=0,
                )
            ],
        )
