from typing import Any

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import Data
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        lines = read_to_lines(named_file_contents.contents, encoding=None)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, _: str, data: Data) -> Any:
        return data.get_plate_block().to_allotrope()
