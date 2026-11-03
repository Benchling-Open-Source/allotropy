from __future__ import annotations

import csv
from io import StringIO

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.pandas import read_csv

SAMPLE_HEADER_KEY = "Sample ID"
REAGENT_HEADER_KEY = "Part number"
IMAGE_HEADER_KEY = "Image#"
TOTAL_ROW_KEY = "Total"


def _flatten_detail_block(rows: list[list[str]]) -> dict[str, str]:
    """Flatten one sample of the per-image detail export into a single summary row.

    A block is: sample settings header + values, a reagent table, then a per-image
    results table ending in a "Total" row that holds the sample-level results.
    """
    header, values = list(rows[0]), list(rows[1])
    starts = [row[0] if row else "" for row in rows]

    image_idx = starts.index(IMAGE_HEADER_KEY)
    if REAGENT_HEADER_KEY in starts:
        reagent_idx = starts.index(REAGENT_HEADER_KEY)
        reagent_rows = [row for row in rows[reagent_idx + 1 : image_idx] if any(row)]
        # Only a single reagent can be represented as flat custom info.
        if len(reagent_rows) == 1:
            header += rows[reagent_idx]
            values += reagent_rows[0]

    total = next(
        row for row in rows[image_idx + 1 :] if row and row[0] == TOTAL_ROW_KEY
    )
    header += rows[image_idx][1:]
    values += total[1:]
    return dict(zip(header, values, strict=False))


def _read_detail_export(rows: list[list[str]]) -> pd.DataFrame:
    block_starts = [
        i for i, row in enumerate(rows) if row and row[0] == SAMPLE_HEADER_KEY
    ]
    samples = [
        _flatten_detail_block(rows[start:end])
        for start, end in zip(block_starts, [*block_starts[1:], len(rows)], strict=True)
    ]
    # Write all samples to one CSV and read it once, so column types are inferred
    # across every sample the same way as for the summary export.
    header = list(dict.fromkeys(key for sample in samples for key in sample))
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header)
    writer.writeheader()
    writer.writerows(samples)
    buffer.seek(0)
    return read_csv(buffer, index_col=False)


class ViCellBluReader:
    SUPPORTED_EXTENSIONS = "csv"

    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        text = "\n".join(read_to_lines(named_file_contents))
        rows = list(csv.reader(StringIO(text)))
        if not cls.is_detail_export(rows):
            return read_csv(StringIO(text), index_col=False)
        return _read_detail_export(rows)

    @staticmethod
    def is_detail_export(rows: list[list[str]]) -> bool:
        return bool(rows and rows[0] and rows[0][0] == SAMPLE_HEADER_KEY) and any(
            row and row[0] == IMAGE_HEADER_KEY for row in rows
        )
