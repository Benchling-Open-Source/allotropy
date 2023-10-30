from collections.abc import Iterator
from io import IOBase, StringIO
from re import search
from typing import Optional

import chardet
import pandas as pd

from allotropy.allotrope.allotrope import AllotropyError


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

    def match(self, pattern: str) -> bool:
        line = self.get()
        return False if line is None else bool(search(pattern, line))

    def is_empty(self) -> bool:
        return self.match("^\\s*$")

    def pop(self) -> Optional[str]:
        line = self.get()
        if line is not None:
            self.current_line += 1
        return line

    def pop_if_match(self, pattern: str) -> Optional[str]:
        if self.match(pattern):
            return self.pop()
        return None

    def pop_data(self) -> Optional[str]:
        self.drop_empty()
        return self.pop()

    def drop_until(self, pattern: str) -> Optional[str]:
        while self.current_line_exists() and not self.match(pattern):
            self.pop()
        return self.get()

    def drop_empty(self) -> Optional[str]:
        while self.current_line_exists() and self.is_empty():
            self.pop()
        return self.get()

    def drop_until_empty(self) -> Optional[str]:
        while self.current_line_exists() and not self.is_empty():
            self.pop()
        return self.get()

    def pop_until(self, pattern: str) -> Iterator[str]:
        while self.current_line_exists() and not self.match(pattern):
            line = self.pop()
            if line is not None:
                yield line

    def pop_until_empty(self) -> Iterator[str]:
        while self.current_line_exists() and not self.is_empty():
            line = self.pop()
            if line is not None:
                yield line


class CsvReader(LinesReader):
    def pop_csv_block(self, pattern: Optional[str] = None) -> pd.DataFrame:
        self.drop_empty()
        if pattern:
            if not self.match(pattern):
                msg = f"Did not find {pattern}"
                raise AllotropyError(msg)
            self.pop()  # remove title

        csv_stream = StringIO("\n".join(self.pop_until_empty()))
        self.drop_empty()

        return pd.read_csv(csv_stream, header=None)

    def drop_sections(self, pattern: str) -> None:
        self.drop_empty()
        while True:
            if not self.match(pattern):
                return
            self.drop_until_empty()
            self.drop_empty()
