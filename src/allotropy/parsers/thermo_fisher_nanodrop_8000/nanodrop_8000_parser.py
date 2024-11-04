from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_8000.nanodrop_8000_reader import (
    Nanodrop8000Reader,
)
from allotropy.parsers.thermo_fisher_nanodrop_8000.nanodrop_8000_structure import (
    create_measurement_group,
    create_metadata,
    SpectroscopyRow,
)
from allotropy.parsers.utils.pandas import map_rows
from allotropy.parsers.vendor_parser import VendorParser


class Nanodrop8000Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Thermo Fisher Scientific NanoDrop 8000"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = Nanodrop8000Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = Nanodrop8000Reader(named_file_contents)
        rows = map_rows(reader.data, SpectroscopyRow.create)

        return Data(
            create_metadata(named_file_contents.original_file_path),
            measurement_groups=[create_measurement_group(row) for row in rows],
            # NOTE: in current implementation, calculated data is reported at global level for some reason.
            # TODO(nstender): should we move this inside of measurements?
            calculated_data=[item for row in rows for item in row.calculated_data],
        )
