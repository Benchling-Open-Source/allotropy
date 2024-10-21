from collections import defaultdict

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.cfxmaestro.cfxmaestro_reader import (
    CFXMaestroReader,
)
from allotropy.parsers.cfxmaestro.cfxmaestro_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.cfxmaestro.constants import DISPLAY_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.vendor_parser import VendorParser


class CfxmaestroParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = CFXMaestroReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = CFXMaestroReader.create(named_file_contents)
        plate_data = reader.data
        measurements_per_well = defaultdict(list)
        unique_wells = set() #Added unique_wells to get an intager values for the total number of wells
        for _, row in plate_data.iterrows():
            well_row = SeriesData(row)
            well = well_row.get(str, "Well")
            measurements_per_well[well].append(well_row)
            unique_wells.add(well) #Added by PO
        data_measurement = [
            create_measurement_group(measurements, len(unique_wells))
            for measurements in measurements_per_well.values()
        ]

        return Data(
            create_metadata(named_file_contents.original_file_name),
            data_measurement
        )
