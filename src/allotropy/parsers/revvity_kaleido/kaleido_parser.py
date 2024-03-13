from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    Model,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.vendor_parser import VendorParser


class KaleidoParser(VendorParser):
    def to_allotrope(self, _: NamedFileContents) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )
