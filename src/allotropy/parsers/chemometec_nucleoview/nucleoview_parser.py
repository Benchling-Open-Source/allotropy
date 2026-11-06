from allotropy.allotrope.models.adm.cell_counting.rec._2024._09.cell_counting import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.chemometec_nucleoview.nucleoview_structure import (
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows
from allotropy.parsers.vendor_parser import VendorParser


class ChemometecNucleoviewParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "ChemoMetec Nucleoview"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = NucleoviewReader.SUPPORTED_EXTENSIONS
    SUPPORTED_DETECTION_MODES = "Dark Field"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            named_file_contents.contents.seek(0)
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            if "Viability (%)" not in text:
                return False
            lines = text.splitlines()
            for line in lines[:5]:
                if ":\t" in line or ";" in line:
                    return True
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        df = NucleoviewReader.read(named_file_contents.contents)
        data_groups = map_rows(df, create_measurement_groups)
        calculated_data = [
            item for group in data_groups if group[1] is not None for item in group[1]
        ]
        measurement_groups = [group[0] for group in data_groups]
        return Data(
            create_metadata(
                df_to_series_data(df.head(1)), named_file_contents.original_file_path
            ),
            measurement_groups,
            calculated_data,
        )
