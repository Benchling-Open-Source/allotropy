from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    Model,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        LinesReader(lines)
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )
