import io
from typing import Any

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.moldev_softmax_pro.block_factory import create_block
from allotropy.parsers.moldev_softmax_pro.plate_block import PlateBlock
from allotropy.parsers.vendor_parser import VendorParser

BLOCKS_LINE_PREFIX = "##BLOCKS= "
END_LINE_PREFIX = "~End"


class SoftmaxproParser(VendorParser):
    def _parse(self, contents: io.IOBase, filename: str) -> Any:  # noqa: ARG002
        file_contents = self._read_contents(contents)
        lines = file_contents.split("\n")

        # TODO parse whole file, not just blocks
        blocks_line = lines[0]
        if not blocks_line.startswith(BLOCKS_LINE_PREFIX):
            error = f"unrecognized start line {blocks_line}"
            raise AllotropeConversionError(error)

        num_blocks = int(blocks_line[len(BLOCKS_LINE_PREFIX) :])
        blocks = []
        current_block: list[str] = []
        for line in lines[1:]:
            if line.startswith(END_LINE_PREFIX):
                blocks.append(create_block(current_block))
                current_block = []
            elif current_block or line.strip():  # drop empty lines between blocks
                current_block.append(line)

        if len(blocks) != num_blocks:
            error = f"expected number of blocks to match {num_blocks}"
            raise AllotropeConversionError(error)

        plate_blocks = [block for block in blocks if isinstance(block, PlateBlock)]
        if len(plate_blocks) != 1:
            block_types = [block.BLOCK_TYPE for block in blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"expected exactly 1 plate block, got {block_counts}"
            raise AllotropeConversionError(error)
        return plate_blocks[0].to_allotrope()
