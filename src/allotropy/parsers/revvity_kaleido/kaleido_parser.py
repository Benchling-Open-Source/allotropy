from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import VendorParser


class KaleidoParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Revvity Kaleido"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SCHEMA_MAPPER = Mapper
    SUPPORTED_EXTENSIONS = "csv"

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read()
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            for line in reversed(lines):
                stripped = line.strip()
                if stripped:
                    return "Exported with Kaleido" in stripped
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        data = create_data(CsvReader(read_to_lines(named_file_contents)))
        return Data(
            create_metadata(data, named_file_contents.original_file_path),
            create_measurement_groups(data),
        )
