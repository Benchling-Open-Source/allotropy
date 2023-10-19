from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.block_factory import create_block
from allotropy.parsers.moldev_softmax_pro.plate_block import Block, PlateBlock

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"


@dataclass
class BlockList:
    blocks: list[Block]

    @staticmethod
    def create(lines_reader: LinesReader) -> BlockList:
        return BlockList(
            blocks=[
                create_block(block) for block in BlockList._iter_blocks(lines_reader)
            ]
        )

    @staticmethod
    def _get_n_blocks(lines_reader: LinesReader) -> int:
        if search_result := re.search(BLOCKS_LINE_REGEX, lines_reader.pop() or ""):
            return int(search_result.group(1))
        error = "unrecognized start line"
        raise AllotropeConversionError(error)

    @staticmethod
    def _iter_blocks(lines_reader: LinesReader) -> Iterator[list[str]]:
        n_blocks = BlockList._get_n_blocks(lines_reader)
        for _ in range(n_blocks):
            yield list(lines_reader.pop_until(END_LINE_REGEX))
            lines_reader.pop()  # drop end line
            lines_reader.drop_empty()


@dataclass
class Data:
    block_list: BlockList

    def get_plate_block(self) -> PlateBlock:
        plate_blocks = [
            block for block in self.block_list.blocks if isinstance(block, PlateBlock)
        ]

        if len(plate_blocks) != 1:
            block_types = [block.BLOCK_TYPE for block in self.block_list.blocks]
            block_counts = {bt: block_types.count(bt) for bt in set(block_types)}
            error = f"expected exactly 1 plate block, got {block_counts}"
            raise AllotropeConversionError(error)

        return plate_blocks[0]

    @staticmethod
    def create(lines_reader: LinesReader) -> Data:
        return Data(block_list=BlockList.create(lines_reader))
