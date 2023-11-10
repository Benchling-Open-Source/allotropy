from collections.abc import Iterator
from io import IOBase, StringIO
from re import search
from typing import Optional

import chardet
import pandas as pd

from allotropy.allotrope.allotrope import AllotropyError

EMPTY_STR_PATTERN = r"^\s*$"


class LinesReader:
    def __init__(self, io_: IOBase, encoding: Optional[str] = "UTF-8"):
        stream_contents = io_.read()
        self.raw_contents = (
            self._decode(stream_contents, encoding)
            if isinstance(stream_contents, bytes)
            else stream_contents
        )
        self.contents = self.raw_contents.replace("\r\n", "\n")
        self.lines: list[str] = self.contents.split("\n")
        self.n_lines = len(self.lines)
        self.current_line = 0

    def _decode(self, bytes_content: bytes, encoding: Optional[str]) -> str:
        if not encoding:
            encoding = chardet.detect(bytes_content)["encoding"]
            if not encoding:
                error = "Unable to detect input file encoding"
                raise AllotropyError(error)
        return bytes_content.decode(encoding)

    def current_line_exists(self) -> bool:
        return 0 <= self.current_line < self.n_lines

    def get(self) -> Optional[str]:
        return self.lines[self.current_line] if self.current_line_exists() else None

    def match(self, match_pat: str) -> bool:
        line = self.get()
        return False if line is None else bool(search(match_pat, line))

    def is_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> bool:
        return self.match(empty_pat)

    def pop(self) -> Optional[str]:
        line = self.get()
        if line is not None:
            self.current_line += 1
        return line

    def pop_if_match(self, match_pat: str) -> Optional[str]:
        if self.match(match_pat):
            return self.pop()
        return None

    def pop_data(self) -> Optional[str]:
        self.drop_empty()
        return self.pop()

    def drop_until(self, match_pat: str) -> Optional[str]:
        while self.current_line_exists() and not self.match(match_pat):
            self.pop()
        return self.get()

    def drop_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> Optional[str]:
        while self.current_line_exists() and self.is_empty(empty_pat):
            self.pop()
        return self.get()

    def drop_until_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> Optional[str]:
        while self.current_line_exists() and not self.is_empty(empty_pat):
            self.pop()
        return self.get()

    def pop_until(self, match_pat: str) -> Iterator[str]:
        while self.current_line_exists() and not self.match(match_pat):
            line = self.pop()
            if line is not None:
                yield line

    def pop_until_empty(self, empty_pat: str = EMPTY_STR_PATTERN) -> Iterator[str]:
        while self.current_line_exists() and not self.is_empty(empty_pat):
            line = self.pop()
            if line is not None:
                yield line


class CsvReader(LinesReader):
    def pop_csv_block_as_lines(
        self, match_pat: Optional[str] = None, empty_pat: str = EMPTY_STR_PATTERN
    ) -> list:
        self.drop_empty(empty_pat)
        if match_pat:
            if not self.match(match_pat):
                msg = f"Did not find {match_pat}"
                raise AllotropyError(msg)
            self.pop()  # remove title
        lines = list(self.pop_until_empty(empty_pat))
        self.drop_empty(empty_pat)
        return lines

    def pop_csv_block_as_df(
        self,
        match_pat: Optional[str] = None,
        empty_pat: str = EMPTY_STR_PATTERN,
        *,
        as_str: bool = False,
    ) -> Optional[pd.DataFrame]:
        lines = self.pop_csv_block_as_lines(match_pat, empty_pat)
        if not lines:
            return None
        csv_stream = StringIO("\n".join(lines))
        if as_str:
            return pd.read_csv(csv_stream, header=None, dtype=str)
        else:
            return pd.read_csv(csv_stream, header=None)

    def drop_sections(self, match_pat: str) -> None:
        self.drop_empty()
        while True:
            if not self.match(match_pat):
                return
            self.drop_until_empty()
            self.drop_empty()
