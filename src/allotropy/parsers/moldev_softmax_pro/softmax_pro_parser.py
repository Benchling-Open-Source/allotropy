from typing import Any

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import Data
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        contents = named_file_contents.contents
        lines_reader = LinesReader(contents)
        data = Data.create(lines_reader)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Any:
        return data.get_plate_block().to_allotrope()
