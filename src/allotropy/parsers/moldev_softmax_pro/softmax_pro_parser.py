import io
from typing import Any

from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import Data
from allotropy.parsers.vendor_parser import VendorParser


class SoftmaxproParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Any:  # noqa: ARG002
        lines_reader = LinesReader(contents)
        data = Data.create(lines_reader)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Any:
        return data.get_plate_block().to_allotrope()
