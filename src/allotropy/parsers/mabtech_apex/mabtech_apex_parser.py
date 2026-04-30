from collections import defaultdict

import openpyxl

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.mabtech_apex.mabtech_apex_reader import MabtechApexReader
from allotropy.parsers.mabtech_apex.mabtech_apex_structure import (
    create_measurement_group,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import (
    SeriesData,
)
from allotropy.parsers.vendor_parser import VendorParser


class MabtechApexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Mabtech Apex"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = MabtechApexReader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            wb = openpyxl.load_workbook(
                named_file_contents.get_bytes_stream(), read_only=True
            )
            sheet_names = set(wb.sheetnames)
            wb.close()
            has_plate_info = (
                "Plate Information" in sheet_names or "Plate Info" in sheet_names
            )
            return has_plate_info and "Plate Database" in sheet_names
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = MabtechApexReader.create(named_file_contents)

        # if Read Date or machine ID is not present in file, return None, no measurement for given Well
        plate_data = reader.data.dropna(subset=["Read Date", "Machine ID"])
        measurements_per_well = defaultdict(list)
        for _, row in plate_data.iterrows():
            well_row = SeriesData(row)
            well = well_row.get(str, "Well")
            measurements_per_well[well].append(well_row)

        data_measurement = [
            create_measurement_group(measurements, reader.plate_info)
            for measurements in measurements_per_well.values()
        ]
        data = Data(
            create_metadata(reader.plate_info, named_file_contents.original_file_path),
            data_measurement,
        )
        return data
