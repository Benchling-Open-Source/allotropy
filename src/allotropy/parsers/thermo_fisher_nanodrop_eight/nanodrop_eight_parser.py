from functools import partial
import re

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
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.vendor_parser import VendorParser


class NanodropEightParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Thermo Fisher Scientific NanoDrop Eight"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = NanodropEightReader.SUPPORTED_EXTENSIONS

    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            nanodrop_headers = {"application", "serial number", "user name"}
            found = set()
            for line in lines[:5]:
                if re.match(r"^[^\t]+:\t", line):
                    key = line.split(":\t")[0].strip().lower()
                    if key in nanodrop_headers:
                        found.add(key)
            return len(found) >= 2
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = NanodropEightReader(named_file_contents)
        rows = map_rows(
            reader.data, partial(SpectroscopyRow.create, header=reader.header)
        )
        metadata = create_metadata(
            reader.header, named_file_contents.original_file_path
        )

        return Data(
            metadata=metadata,
            measurement_groups=[
                create_measurement_group(
                    row, reader.header, SeriesData(reader.data.iloc[0])
                )
                for row in rows
            ],
            # NOTE: in current implementation, calculated data is reported at global level for some reason.
            # TODO(nstender): should we move this inside of measurements?
            calculated_data=[item for row in rows for item in row.calculated_data],
        )
