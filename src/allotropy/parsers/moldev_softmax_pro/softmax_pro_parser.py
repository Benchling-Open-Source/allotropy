from typing import Any

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import Data
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Any:
        reader = CsvReader(named_file_contents.contents, encoding=None)
        data = Data.create(reader)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Any:
        return data.get_plate_block().to_allotrope()
