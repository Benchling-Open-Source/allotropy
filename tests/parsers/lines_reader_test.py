from io import BytesIO
import re
from typing import Optional

import pytest

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader, read_to_lines

INPUT_LINES = [
    "data section",
    "col1, col2, col3",
    ", ,",
    ", ,",
    ", ,",
    "",
    "header section",
    "element1",
    "element2",
    "element3",
    "",
    "",
    "information",
    "name",
    "123",
    "",
]


def _read_to_lines(encoding: Optional[str] = None) -> list[str]:
    input_text = "\n".join(INPUT_LINES)
    io_ = BytesIO(input_text.encode("UTF-8"))
    named_file_contents = NamedFileContents(io_, "test.csv", encoding)
    return read_to_lines(named_file_contents)


def test_read_to_lines() -> None:
    lines = _read_to_lines()
    assert lines == INPUT_LINES


@pytest.mark.parametrize("encoding", [None, "UTF-8"])
def test_read_to_lines_with_encoding(encoding: Optional[str]) -> None:
    lines = _read_to_lines(encoding)
    assert lines == INPUT_LINES


def test_read_to_lines_with_encoding_that_is_invalid() -> None:
    # TODO: should raise AllotropeConversionError
    with pytest.raises(LookupError, match="unknown encoding: BAD ENCODING"):
        _read_to_lines("BAD ENCODING")


def test_read_to_lines_with_encoding_that_is_valid_but_invalid_for_file() -> None:
    expected_regex_raw = "'utf-32-le' codec can't decode bytes in position 0-3: code point not in range(0x110000)"
    expected_regex = re.escape(expected_regex_raw)
    # TODO: should raise AllotropeConversionError
    with pytest.raises(UnicodeDecodeError, match=expected_regex):
        _read_to_lines("UTF-32")


def get_test_reader() -> LinesReader:
    return LinesReader(INPUT_LINES)


def test_reader_init() -> None:
    test_reader = get_test_reader()
    assert test_reader.lines == INPUT_LINES
    assert test_reader.current_line == 0


def test_current_line_exists() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = -1
    assert not test_reader.current_line_exists()

    test_reader.current_line = 1
    assert test_reader.current_line_exists()

    test_reader.current_line = 16
    assert not test_reader.current_line_exists()


def test_reader_get() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 0
    assert test_reader.get() == "data section"

    test_reader.current_line = 6
    assert test_reader.get() == "header section"

    test_reader.current_line = 16
    assert test_reader.get() is None


def test_reader_match() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 6
    assert test_reader.match("^header section")

    test_reader.current_line = 12
    assert test_reader.match("^information")

    test_reader.current_line = 0
    assert not test_reader.match("^BAD PATTERN$")


def test_reader_is_empty() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 1
    assert not test_reader.is_empty()

    test_reader.current_line = 5
    assert test_reader.is_empty()


def test_reader_pop() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 6
    assert test_reader.pop() == "header section"
    assert test_reader.current_line == 7

    test_reader.current_line = 15
    assert test_reader.pop() == ""
    assert test_reader.current_line == 16
    assert test_reader.pop() is None
    assert test_reader.current_line == 16


def test_reader_pop_data() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 10
    assert test_reader.pop_data() == "information"
    assert test_reader.current_line == 13

    test_reader.current_line = 16
    assert test_reader.pop_data() is None
    assert test_reader.current_line == 16


def test_reader_drop_until() -> None:
    test_reader = get_test_reader()
    assert test_reader.drop_until("^header section") == "header section"
    assert test_reader.current_line == 6

    assert test_reader.drop_until("^BAD PATTERN$") is None
    assert test_reader.current_line == 16


def test_reader_drop_empty() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 10
    assert test_reader.drop_empty() == "information"
    assert test_reader.current_line == 12

    test_reader.current_line = 15
    assert test_reader.drop_empty() is None
    assert test_reader.current_line == 16


def test_reader_drop_until_empty() -> None:
    test_reader = get_test_reader()
    assert test_reader.drop_until_empty() == ""
    assert test_reader.current_line == 5

    test_reader.current_line = 16
    assert test_reader.drop_until_empty() is None
    assert test_reader.current_line == 16


def test_reader_pop_until() -> None:
    test_reader = get_test_reader()
    assert list(test_reader.pop_until("^header section")) == INPUT_LINES[:6]


def test_reader_pop_until_empty() -> None:
    test_reader = get_test_reader()
    assert list(test_reader.pop_until_empty()) == INPUT_LINES[:5]
