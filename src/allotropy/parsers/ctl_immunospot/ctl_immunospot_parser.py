from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    Model,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.ctl_immunospot.ctl_immunospot_structure import Data
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = LinesReader(lines)
        data = Data.create(reader)
        file_name = named_file_contents.original_file_name
        return self._get_model(data, file_name)

    def _get_model(self, data: Data, file_name: str) -> Model:  # noqa: ARG002
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )
