from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.methodical_mind.methodical_mind_reader import (
    MethodicalMindReader,
)
from allotropy.parsers.methodical_mind.methodical_mind_structure import (
    create_measurement_groups,
    create_metadata,
    Header,
    PlateData,
)
from allotropy.parsers.msd_workbench.msd_workbench_calculated_data_mapping import (
    create_calculated_data_groups,
)
from allotropy.parsers.msd_workbench.msd_workbench_reader import (
    MSDWorkbenchReader,
)
from allotropy.parsers.msd_workbench.msd_workbench_structure import (
    create_measurement_groups as create_msd_measurement_groups,
    create_metadata as create_msd_metadata,
    PlateData as MSDPlateData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class MSDWorkbenchParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "MSD Discovery Workbench"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = MSDWorkbenchReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        if named_file_contents.extension == "txt":
            return self._process_methodical_mind(named_file_contents)
        return self._process_msd_workbench(named_file_contents)

    def _process_methodical_mind(self, named_file_contents: NamedFileContents) -> Data:
        reader = MethodicalMindReader(named_file_contents)
        metadata = create_metadata(
            Header.create(reader.plate_headers[0]),
            named_file_contents.original_file_path,
        )
        plate_data_objects = [PlateData.create(header, data) for header, data in reader]
        measurement_groups = create_measurement_groups(plate_data_objects)
        return Data(metadata, measurement_groups)

    def _process_msd_workbench(self, named_file_contents: NamedFileContents) -> Data:
        reader = MSDWorkbenchReader(named_file_contents)
        plate_data = MSDPlateData.create(reader.plate_data, reader.well_plate_id)
        measurement_groups = create_msd_measurement_groups(plate_data)
        measurements = [
            measurement
            for group in measurement_groups
            for measurement in group.measurements
        ]
        calculated_data_groups = create_calculated_data_groups(
            reader.plate_data, measurements
        )
        metadata = create_msd_metadata(named_file_contents.original_file_path)
        return Data(metadata, measurement_groups, calculated_data_groups)
