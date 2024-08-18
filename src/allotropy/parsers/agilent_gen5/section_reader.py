from __future__ import annotations

from collections.abc import Iterator

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader, read_to_lines


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
