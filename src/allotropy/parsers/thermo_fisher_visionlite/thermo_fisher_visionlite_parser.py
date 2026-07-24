from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_visionlite.constants import DISPLAY_NAME
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_reader import (
    ThermoFisherVisionliteReader,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_structure import (
    VisionLiteData,
)
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherVisionliteParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = ThermoFisherVisionliteReader.SUPPORTED_EXTENSIONS
    SUPPORTED_DETECTION_MODES = "Absorbance"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            named_file_contents.contents.seek(0)
            raw = named_file_contents.contents.read(8192)
            if isinstance(raw, bytes):
                if raw[:2] == b"\xff\xfe":
                    text = raw[2:].decode("utf-16-le", errors="replace")
                elif raw[:2] == b"\xfe\xff":
                    text = raw[2:].decode("utf-16-be", errors="replace")
                else:
                    text = raw.decode("utf-8", errors="replace")
            else:
                text = raw
            lines = text.splitlines()
            if not lines:
                return False
            first = lines[0].lower().strip()
            if first.startswith("sample name") or first.startswith("well position"):
                return True
            # Scan/kinetic format: second line starts with "nm,"
            if len(lines) > 1 and lines[1].strip().startswith("nm,"):
                return True
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        return VisionLiteData.create(
            ThermoFisherVisionliteReader(named_file_contents),
            named_file_contents.original_file_path,
        )
