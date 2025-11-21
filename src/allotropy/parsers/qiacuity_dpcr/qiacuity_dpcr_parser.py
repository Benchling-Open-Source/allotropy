from __future__ import annotations

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import Model
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Mapper,
    MeasurementGroup,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_calculated_data import (
    create_calculated_data as create_qiacuity_calculated_data,
)
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_reader import QiacuitydPCRReader
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_structure import (
    create_measurements,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class QiacuitydPCRParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Qiacuity dPCR"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = QiacuitydPCRReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = QiacuitydPCRReader(named_file_contents)
        # Assign stable measurement identifiers per row for data source linkage
        reader.well_data["_measurement_identifier"] = [
            random_uuid_str() for _ in range(len(reader.well_data))
        ]
        # Build SeriesData list once and reuse
        series_rows: list[SeriesData] = [
            SeriesData(row) for _, row in reader.well_data.iterrows()
        ]
        calculated_data = create_qiacuity_calculated_data(series_rows)
        measurement_groups = [
            MeasurementGroup(
                measurements=[create_measurements(row) for row in series_rows],
                # TODO: Hardcoded plate well count to 0 since it's a required field
                #  ASM will be modified to optional in future version
                plate_well_count=0,
            )
        ]
        return Data(
            create_metadata(named_file_contents.original_file_path),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )
