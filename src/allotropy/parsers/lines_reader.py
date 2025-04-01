from __future__ import annotations

from collections.abc import Iterator
from io import StringIO
from re import search
from typing import Any, Literal

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.encoding import decode
from allotropy.parsers.utils.pandas import read_csv
from allotropy.parsers.utils.values import assert_not_none

EMPTY_STR_PATTERN = r"^\s*$"
# Use to match empty line in a CSV file
EMPTY_CSV_LINE = r"^,*$"
# Use to match empty string or empty CSV line
EMPTY_STR_OR_CSV_LINE = r"^[\s,]*$"


def read_to_lines(named_file_contents: NamedFileContents) -> list[str]:
    raw_contents = decode(named_file_contents.contents, named_file_contents.encoding)
    contents = raw_contents.replace("\r\n", "\n")
    return contents.split("\n")


class LinesReader:
    lines: list[str]
    current_line: int

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> LinesReader:
        return LinesReader(read_to_lines(named_file_contents))

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.current_line = 0

    def line_exists(self, line: int) -> bool:
        return 0 <= line < len(self.lines)

    def current_line_exists(self) -> bool:
        return self.line_exists(self.current_line)

    def get_line(self, line: int) -> str | None:
        return self.lines[line] if self.line_exists(line) else None

    def get(self) -> str | None:
        return self.lines[self.current_line] if self.current_line_exists() else None

    def match(self, match_pat: str) -> bool:
        line = self.get()
        return False if line is None else bool(search(match_pat, line))

    def is_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> bool:
        return self.match(empty_pat)

    def pop(self) -> str | None:
        line = self.get()
        if line is not None:
            self.current_line += 1
        return line

    def pop_if_match(self, match_pat: str) -> str | None:
        return self.pop() if self.match(match_pat) else None

    def pop_data(self) -> str | None:
        self.drop_empty()
        return self.pop()

    def drop_until(self, match_pat: str) -> str | None:
        while self.current_line_exists() and not self.match(match_pat):
            self.pop()
        return self.get()

    def drop_until_inclusive(self, match_pat: str) -> str | None:
        self.drop_until(match_pat)
        return self.pop()

    def drop_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> str | None:
        while self.current_line_exists() and self.is_empty(empty_pat):
            self.pop()
        return self.get()

    def drop_until_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> str | None:
        while self.current_line_exists() and not self.is_empty(empty_pat):
            self.pop()
        return self.get()

    def drop_until_empty_inclusive(
        self, empty_pat: str = EMPTY_STR_PATTERN
    ) -> str | None:
        self.drop_until_empty(empty_pat)
        return self.pop()

    def pop_while(self, match_pat: str) -> Iterator[str]:
        while self.current_line_exists() and self.match(match_pat):
            line = self.pop()
            if line is not None:
                yield line

    def pop_until(self, match_pat: str) -> Iterator[str]:
        while self.current_line_exists() and not self.match(match_pat):
            line = self.pop()
            if line is not None:
                yield line

    def pop_until_inclusive(self, match_pat: str) -> Iterator[str]:
        yield from self.pop_until(match_pat)
        if self.current_line_exists():
            yield assert_not_none(self.pop())

    def pop_until_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> Iterator[str]:
        while self.current_line_exists() and not self.is_empty(empty_pat):
            line = self.pop()
            if line is not None:
                yield line


class SectionLinesReader(LinesReader):
    @staticmethod
    def create(named_file_contents: NamedFileContents) -> SectionLinesReader:
        return SectionLinesReader(read_to_lines(named_file_contents))

    def iter_sections(self, pattern: str) -> Iterator[LinesReader]:
        self.drop_until(pattern)
        while True:
            if (initial_line := self.pop()) is None:
                break
            lines = [initial_line, *self.pop_until(pattern)]
            yield LinesReader(lines)


class InvertedLinesReader(LinesReader):
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.current_line = len(lines) - 1

    def pop(self) -> str | None:
        line = self.get()
        if line is not None:
            self.current_line -= 1
        return line


class CsvReader(LinesReader):
    @staticmethod
    def create(named_file_contents: NamedFileContents) -> CsvReader:
        return CsvReader(read_to_lines(named_file_contents))

    def pop_csv_block_as_lines(self, empty_pat: str = EMPTY_STR_PATTERN) -> list[str]:
        self.drop_empty(empty_pat)
        lines = list(self.pop_until_empty(empty_pat))
        self.drop_empty(empty_pat)
        return lines

    def pop_csv_block_as_df(
        self,
        empty_pat: str = EMPTY_STR_PATTERN,
        header: int | Literal["infer"] | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame | None:
        if lines := self.pop_csv_block_as_lines(empty_pat):
            return read_csv(
                StringIO("\n".join(lines)),
                # Prevent pandas from rounding decimal values, at the cost of some speed.
                float_precision="round_trip",
                header=header,
                **kwargs,
            )
        return None

    def drop_sections(self, match_pat: str) -> None:
        self.drop_empty()
        while self.match(match_pat):
            self.drop_until_empty()
            self.drop_empty()

    def pop_as_series(self, sep: str = " ") -> pd.Series[str] | None:
        line = self.pop()
        return None if line is None else pd.Series(line.split(sep))

    def lines_as_df(
        self,
        lines: list[str],
        header: int | Literal["infer"] | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame | None:
        if lines:
            return read_csv(
                StringIO("\n".join(lines)),
                dtype=None,
                # Prevent pandas from rounding decimal values, at the cost of some speed.
                float_precision="round_trip",
                header=header,
                **kwargs,
            )
        return None
