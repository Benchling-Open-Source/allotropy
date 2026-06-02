from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.luminex_intelliflex.constants import DISPLAY_NAME
from allotropy.parsers.luminex_intelliflex.luminex_intelliflex_structure import (
    create_metadata,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    create_measurement_groups,
    Data as XponentData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class LuminexIntelliflexParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = LuminexXponentReader.SUPPORTED_EXTENSIONS
    SUPPORTED_DETECTION_MODES = "Fluorescence"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            if not lines:
                return False
            first_line = lines[0]
            if (
                "INSTRUMENT TYPE" in first_line
                and "WELL LOCATION" in first_line
                and "SAMPLE ID" in first_line
            ):
                return True
            for line in lines:
                stripped = line.strip()
                if stripped:
                    return stripped.startswith("Program,") or stripped.startswith(
                        '"Program",'
                    )
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = LuminexXponentReader(named_file_contents)
        data = XponentData.create(reader)
        return Data(
            create_metadata(
                data.header, data.calibrations, named_file_contents.original_file_path
            ),
            *create_measurement_groups(data.measurement_list.measurements, data.header),
        )
