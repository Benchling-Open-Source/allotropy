from collections.abc import Iterator

from allotropy.parsers.lines_reader import LinesReader, ListReader


class SectionLinesReader(LinesReader):
    def iter_sections(self, pattern: str) -> Iterator[LinesReader]:
        self.drop_until(pattern)
        while True:
            if (initial_line := self.pop()) is None:
                break
            lines = [initial_line, *self.pop_until(pattern)]
            yield ListReader(lines)
