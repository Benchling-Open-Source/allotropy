from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_calcdocs import (
    create_calculated_data,
)
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    create_measurement_groups,
    create_metadata,
    Data as StructureData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class PerkinElmerEnvisionParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "PerkinElmer Envision"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "csv"
    SUPPORTED_DETECTION_MODES = "Absorbance, Fluorescence, Luminescence"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            lines = text.splitlines()
            for line in lines[:20]:
                if line.startswith("Plate information"):
                    return True
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = StructureData.create(reader)

        return Data(
            create_metadata(
                data.software, data.instrument, named_file_contents.original_file_path
            ),
            create_measurement_groups(data),
            create_calculated_data(data.plate_list, data.labels.get_read_type()),
        )
