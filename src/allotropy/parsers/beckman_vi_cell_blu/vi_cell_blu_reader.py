from __future__ import annotations

import csv
from io import StringIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.pandas import read_csv

SAMPLE_HEADER_KEY = "Sample ID"
REAGENT_HEADER_KEY = "Part number"
IMAGE_HEADER_KEY = "Image#"
TOTAL_ROW_KEY = "Total"
RESULTS_KEY = "Viability (%)"


def _find_table_header(rows: list[list[str]], key: str) -> int | None:
    # Rows 0 and 1 are the sample settings header and values; a sample value can
    # match a table key, so table headers are only searched for after them.
    return next(
        (i for i, row in enumerate(rows) if i > 1 and row and row[0] == key), None
    )


def _flatten_detail_block(rows: list[list[str]]) -> dict[str, str]:
    """Flatten one sample of the per-image detail export into a single summary row.

    A block is: sample settings header + values, a reagent table, then a per-image
    results table ending in a "Total" row that holds the sample-level results.
    """
    header, values = list(rows[0]), list(rows[1])
    image_idx = _find_table_header(rows, IMAGE_HEADER_KEY)
    if image_idx is None:
        msg = f"Unable to find the '{IMAGE_HEADER_KEY}' table for a sample in the detail export."
        raise AllotropeConversionError(msg)
    reagent_idx = _find_table_header(rows[:image_idx], REAGENT_HEADER_KEY)
    if reagent_idx is not None:
        reagent_rows = [row for row in rows[reagent_idx + 1 : image_idx] if any(row)]
        # Only a single reagent can be represented as flat custom info.
        if len(reagent_rows) == 1:
            header += rows[reagent_idx]
            values += reagent_rows[0]

    total = next(
        (row for row in rows[image_idx + 1 :] if row and row[0] == TOTAL_ROW_KEY),
        None,
    )
    if total is None:
        msg = f"Unable to find the '{TOTAL_ROW_KEY}' row for a sample in the detail export."
        raise AllotropeConversionError(msg)
    header += rows[image_idx][1:]
    values += total[1:]
    return dict(zip(header, values, strict=False))


def _read_detail_export(rows: list[list[str]]) -> pd.DataFrame:
    # Every sample repeats the same settings header, so a sample value can't be
    # mistaken for the start of a new sample.
    block_starts = [i for i, row in enumerate(rows) if row == rows[0]]
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
        # The summary export also starts with "Sample ID" but has the results
        # columns in that first header.
        if not rows or not rows[0] or rows[0][0] != SAMPLE_HEADER_KEY:
            return False
        if RESULTS_KEY in rows[0]:
            return False
        return _find_table_header(rows, IMAGE_HEADER_KEY) is not None
