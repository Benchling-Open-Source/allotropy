from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_reader import (
    NanodropEightReader,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_structure import (
    create_measurement_group,
    create_metadata,
    SpectroscopyRow,
)
from allotropy.parsers.vendor_parser import VendorParser


class NanodropEightParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Thermo Fisher NanoDrop Eight"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = NanodropEightReader.SUPPORTED_EXTENSIONS

    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        data = NanodropEightReader.read(named_file_contents)
        rows = SpectroscopyRow.create_rows(data)
        metadata = create_metadata(named_file_contents.original_file_name, data)

        return Data(
            metadata=metadata,
            measurement_groups=[create_measurement_group(row) for row in rows],
            # NOTE: in current implementation, calculated data is reported at global level for some reason.
            # TODO(nstender): should we move this inside of measurements?
            calculated_data=[item for row in rows for item in row.calculated_data],
        )
