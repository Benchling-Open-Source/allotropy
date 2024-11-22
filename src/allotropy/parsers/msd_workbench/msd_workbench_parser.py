from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.msd_workbench.msd_workbench_calculated_data_mapping import (
    create_calculated_data_groups,
)
from allotropy.parsers.msd_workbench.msd_workbench_reader import (
    MSDWorkbenchReader,
)
from allotropy.parsers.msd_workbench.msd_workbench_structure import (
    create_measurement_groups,
    create_metadata,
    Header,
    PlateData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class MSDWorkbenchParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "MSD Discovery Workbench"
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = MSDWorkbenchReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = MSDWorkbenchReader(named_file_contents)
        plate_data = PlateData.create(reader.plate_data)
        measurement_groups = create_measurement_groups(plate_data)
        measurements = [
            measurement
            for group in measurement_groups
            for measurement in group.measurements
        ]
        calculated_data_groups = create_calculated_data_groups(
            reader.plate_data, measurements
        )

        return Data(
            create_metadata(
                Header.create(named_file_contents.original_file_path),
            ),
            measurement_groups,
            calculated_data_groups,
        )
