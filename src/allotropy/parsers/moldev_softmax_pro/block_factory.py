from allotropy.allotrope.allotrope import AllotropeConversionError
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

DELIMITER = "\t"


def create_plate_block(raw_lines: list[str]) -> PlateBlock:
    split_lines = [
        [value_or_none(value) for value in raw_line.split(DELIMITER)]
        for raw_line in raw_lines
    ]
    header = split_lines[0]
    read_mode = header[5]
    plate_block_cls: type[PlateBlock]
    if read_mode == "Absorbance":
        plate_block_cls = AbsorbancePlateBlock
    elif read_mode == "Fluorescence":
        plate_block_cls = FluorescencePlateBlock
    elif read_mode == "Luminescence":
        plate_block_cls = LuminescencePlateBlock
    else:
        error = f"unrecognized read mode {read_mode}"
        raise AllotropeConversionError(error)
    plate_block = plate_block_cls(header, split_lines, raw_lines)
    return plate_block


ALL_BLOCKS: list[type[Block]] = [GroupBlock, NoteBlock, PlateBlock]
BLOCK_CLS_BY_TYPE = {cls.BLOCK_TYPE: cls for cls in ALL_BLOCKS}


def create_block(lines: list[str]) -> Block:
    for key, block_cls in BLOCK_CLS_BY_TYPE.items():
        if lines[0].startswith(key):
            if block_cls == PlateBlock:
                return create_plate_block(lines)
            return block_cls(lines)
    error = f"unrecognized block {lines[0]}"
    raise AllotropeConversionError(error)
