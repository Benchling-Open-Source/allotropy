import re

from allotropy.allotrope.models.adm.plate_reader.rec._2025._03.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.softmax_pro_data_creator import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    StructureData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Molecular Devices SoftMax Pro"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SUPPORTED_DETECTION_MODES = "Absorbance, Fluorescence, Luminescence"
    SCHEMA_MAPPER = Mapper

    @classmethod
    def sniff(cls, named_file_contents: NamedFileContents) -> bool:
        try:
            raw = named_file_contents.contents.read(8192)
            if isinstance(raw, bytes):
                if raw[:2] == b"\xff\xfe":
                    text = raw[2:].decode("utf-16-le", errors="replace")
                else:
                    text = raw.decode("utf-8", errors="replace")
            else:
                text = raw
            lines = text.splitlines()
            for line in lines:
                if line.strip():
                    return bool(re.match(r"^##BLOCKS=\s*\d+", line))
            return False
        except Exception:
            return False

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = StructureData.create(reader)

        return Data(
            create_metadata(named_file_contents.original_file_path),
            create_measurement_groups(data),
            create_calculated_data(data),
        )
