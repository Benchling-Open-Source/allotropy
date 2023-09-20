from collections.abc import Iterator
from io import IOBase, StringIO
from re import search
from typing import Any, Optional

import pandas as pd


class LinesReader:
    def __init__(self, io_: IOBase):
        raw_contents = io_.read()
        if isinstance(raw_contents, bytes):
            raw_contents = raw_contents.decode("UTF-8")
        self.contents = raw_contents.replace("\r\n", "\n")
        self.lines: list[str] = self.contents.split("\n")
        self.n_lines = len(self.lines)
        self.current_line = 0

    def current_line_exists(self) -> bool:
        return 0 <= self.current_line < self.n_lines

    def get(self) -> Optional[str]:
        return self.lines[self.current_line] if self.current_line_exists() else None

    def match(self, pattern: str) -> bool:
        line = self.get()
        return False if line is None else bool(search(pattern, line))

    def is_empty(self) -> bool:
        return not self.current_line_exists() or self.match("^\\s*$")

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

    def drop_sections(self, pattern: str) -> None:
        self.drop_empty()
        while True:
            if not self.match(pattern):
                return
            self.drop_until_empty()
            self.drop_empty()


class CSVBlockLinesReader(LinesReader):
    def __init__(self, io_: IOBase):
        super().__init__(io_)
        self.default_read_csv_kwargs: dict[str, Any] = {}

    def pop_csv_block(
        self,
        start_pattern: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[pd.DataFrame]:
        self.drop_empty()
        if start_pattern:
            if not self.match(start_pattern):
                return None
            self.pop()  # remove title

        lines = [line for line in self.pop_until_empty() if line]
        self.drop_empty()

        if not lines:
            return None

        kwargs = {**self.default_read_csv_kwargs, **(kwargs or {})}
        data: pd.DataFrame = pd.read_csv(StringIO("\n".join(lines)), **kwargs)
        return data
