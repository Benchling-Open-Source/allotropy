from io import StringIO

import pytest

from allotropy.parsers.lines_reader import CSVBlockLinesReader, LinesReader


def get_input_lines() -> list[str]:
    return [
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


def io_from_lines(lines: list[str]) -> StringIO:
    return StringIO("\n".join(lines))


def get_test_reader() -> LinesReader:
    return LinesReader(io_from_lines(get_input_lines()))


@pytest.mark.short
def test_reader_constructure() -> None:
    test_reader = get_test_reader()
    assert test_reader.contents == "\n".join(get_input_lines())
    assert test_reader.lines == get_input_lines()
    assert test_reader.n_lines == 16
    assert test_reader.current_line == 0


@pytest.mark.short
def test_current_line_exists() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = -1
    assert not test_reader.current_line_exists()

    test_reader.current_line = 1
    assert test_reader.current_line_exists()

    test_reader.current_line = 16
    assert not test_reader.current_line_exists()


@pytest.mark.short
def test_reader_get() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 0
    assert test_reader.get() == "data section"

    test_reader.current_line = 6
    assert test_reader.get() == "header section"

    test_reader.current_line = 16
    assert test_reader.get() is None


@pytest.mark.short
def test_reader_match() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 6
    assert test_reader.match("^header section")

    test_reader.current_line = 12
    assert test_reader.match("^information")

    test_reader.current_line = 0
    assert not test_reader.match("^BAD PATTERN$")


@pytest.mark.short
def test_reader_is_empty() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 1
    assert not test_reader.is_empty()

    test_reader.current_line = 5
    assert test_reader.is_empty()


@pytest.mark.short
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


@pytest.mark.short
def test_reader_pop_if_match() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 5
    assert not test_reader.match("header section")
    assert not test_reader.pop_if_match("header_section")

    test_reader.current_line = 6
    assert test_reader.pop() == "header section"
    assert test_reader.current_line == 7


@pytest.mark.short
def test_reader_pop_data() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 10
    assert test_reader.pop_data() == "information"
    assert test_reader.current_line == 13

    test_reader.current_line = 16
    assert test_reader.pop_data() is None
    assert test_reader.current_line == 16


@pytest.mark.short
def test_reader_drop_until() -> None:
    test_reader = get_test_reader()
    assert test_reader.drop_until("^header section") == "header section"
    assert test_reader.current_line == 6

    assert test_reader.drop_until("^BAD PATTERN$") is None
    assert test_reader.current_line == 16


@pytest.mark.short
def test_reader_drop_empty() -> None:
    test_reader = get_test_reader()
    test_reader.current_line = 10
    assert test_reader.drop_empty() == "information"
    assert test_reader.current_line == 12

    test_reader.current_line = 15
    assert test_reader.drop_empty() is None
    assert test_reader.current_line == 16


@pytest.mark.short
def test_reader_drop_until_empty() -> None:
    test_reader = get_test_reader()
    assert test_reader.drop_until_empty() == ""
    assert test_reader.current_line == 5

    test_reader.current_line = 16
    assert test_reader.drop_until_empty() is None
    assert test_reader.current_line == 16


@pytest.mark.short
def test_reader_pop_until() -> None:
    input_lines = get_input_lines()
    test_reader = get_test_reader()
    assert list(test_reader.pop_until("^header section")) == input_lines[:6]


@pytest.mark.short
def test_reader_pop_until_empty() -> None:
    input_lines = get_input_lines()
    test_reader = get_test_reader()
    assert list(test_reader.pop_until_empty()) == input_lines[:5]


@pytest.mark.short
def test_reader_drop_sections() -> None:
    test_reader = get_test_reader()
    test_reader.drop_sections("^header section|^data section")
    assert test_reader.match("information")


@pytest.mark.short
def test_csv_reader_pop_csv_block_with_title() -> None:
    reader = CSVBlockLinesReader(
        io_from_lines(
            [
                "",
                "Results",
                "COL_1,COL_2,COL_3",
                "1,,2",
                ",3,",
                "",
            ]
        )
    )
    data = reader.pop_csv_block("Results")
    assert data["COL_1"][0] == 1
    assert data["COL_2"][1] == 3
    assert data["COL_3"][0] == 2
    assert reader.is_empty()


@pytest.mark.short
def test_csv_reader_pop_csv_block_without_title() -> None:
    reader = CSVBlockLinesReader(
        io_from_lines(
            ["COL_1,COL_2,COL_3", "1,,2", ",3,", "", "", "New Section", "..."]
        )
    )
    data = reader.pop_csv_block()
    assert data["COL_1"][0] == 1
    assert data["COL_2"][1] == 3
    assert data["COL_3"][0] == 2
    assert reader.match("New Section")


@pytest.mark.short
def test_csv_reader_csv_kwargs() -> None:
    reader = CSVBlockLinesReader(
        io_from_lines(
            [
                "Field section",
                "KEY1=1",
                "KEY2=2",
                "",
                "1,,2",
                ",3,",
            ]
        )
    )
    reader.default_read_csv_kwargs = {"sep": "=", "header": None}
    data = reader.pop_csv_block("Field section")
    assert data[0][0] == "KEY1"
    assert data[1][0] == 1
    assert data[0][1] == "KEY2"
    assert data[1][1] == 2

    data = reader.pop_csv_block(sep=",")
    assert data[0][0] == 1
    assert data[1][1] == 3
    assert data[2][0] == 2
