from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.moldev_softmax_pro.absorbance_plate_block import (
    AbsorbancePlateBlock,
)
from allotropy.parsers.moldev_softmax_pro.fluorescence_plate_block import (
    FluorescencePlateBlock,
)
from allotropy.parsers.moldev_softmax_pro.luminescence_plate_block import (
    LuminescencePlateBlock,
)
from allotropy.parsers.moldev_softmax_pro.plate_block import (
    Block,
    GroupBlock,
    NoteBlock,
    PlateBlock,
)
from allotropy.parsers.utils.values import value_or_none

BLOCKS_LINE_REGEX = r"^##BLOCKS=\s*(\d+)$"
END_LINE_REGEX = "~End"


def create_plate_block(raw_lines: list[str]) -> PlateBlock:
    split_lines = [
        [value_or_none(value) for value in raw_line.split("\t")]
        for raw_line in raw_lines
    ]
    header = split_lines[0]
    read_mode = header[5]

    plate_block_cls = {
        "Absorbance": AbsorbancePlateBlock,
        "Fluorescence": FluorescencePlateBlock,
        "Luminescence": LuminescencePlateBlock,
    }

    if cls := plate_block_cls.get(read_mode or ""):
        return cls(header, split_lines, raw_lines)

    error = f"unrecognized read mode {read_mode}"
    raise AllotropeConversionError(error)


def create_block(lines: list[str]) -> Block:
    all_blocks: list[type[Block]] = [GroupBlock, NoteBlock, PlateBlock]
    block_cls_by_type = {cls.BLOCK_TYPE: cls for cls in all_blocks}

    for key, block_cls in block_cls_by_type.items():
        if lines[0].startswith(key):
            if block_cls == PlateBlock:
                return create_plate_block(lines)
            return block_cls(lines)

    error = f"unrecognized block {lines[0]}"
    raise AllotropeConversionError(error)


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
