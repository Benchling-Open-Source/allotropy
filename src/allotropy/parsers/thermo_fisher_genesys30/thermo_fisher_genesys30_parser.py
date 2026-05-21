from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_genesys30.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_reader import (
    ThermoFisherGenesys30Reader,
)
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherGenesys30Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherGenesys30Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            named_file_contents.contents.seek(0)
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            if not lines:
                return False
            first_line = lines[0]
            sep = "\t" if "\t" in first_line else ","
            parts = first_line.split(sep)
            if len(parts) < 2 or parts[0].strip() != "Scan":
                return False
            return any(
                p.strip().lower() == "mode"
                for p in (lines[1].split(sep) if len(lines) > 1 else [])
            )
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = ThermoFisherGenesys30Reader(named_file_contents)
        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(reader.header, reader.data),
        )
