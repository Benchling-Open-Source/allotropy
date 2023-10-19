from collections.abc import Iterator
import io
import re
from typing import Any

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.block_factory import create_block
from allotropy.parsers.moldev_softmax_pro.plate_block import PlateBlock
from allotropy.parsers.vendor_parser import VendorParser

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"


class SoftmaxproParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Any:  # noqa: ARG002
        lines_reader = LinesReader(contents)
        blocks = [create_block(block) for block in self._iter_blocks(lines_reader)]

        plate_blocks = [block for block in blocks if isinstance(block, PlateBlock)]
        if len(plate_blocks) != 1:
            block_types = [block.BLOCK_TYPE for block in blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"expected exactly 1 plate block, got {block_counts}"
            raise AllotropeConversionError(error)
        return plate_blocks[0].to_allotrope()

    def _get_n_blocks(self, lines_reader: LinesReader) -> int:
        if search_result := re.search(BLOCKS_LINE_REGEX, lines_reader.pop() or ""):
            return int(search_result.group(1))
        error = "unrecognized start line"
        raise AllotropeConversionError(error)

    def _iter_blocks(self, lines_reader: LinesReader) -> Iterator[list[str]]:
        n_blocks = self._get_n_blocks(lines_reader)
        for _ in range(n_blocks):
            yield list(lines_reader.pop_until(END_LINE_REGEX))
            lines_reader.pop()  # drop end line
            lines_reader.drop_empty()
