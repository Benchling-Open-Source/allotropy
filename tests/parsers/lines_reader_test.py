from io import BytesIO

from allotropy.parsers.lines_reader import LinesReader


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


def get_input_text() -> str:
    return "\n".join(get_input_lines())


def get_input_stream() -> BytesIO:
    return BytesIO(get_input_text().encode("UTF-8"))


def get_test_reader() -> LinesReader:
    return LinesReader(get_input_stream())


def test_reader_constructure() -> None:
    test_reader = get_test_reader()
    assert test_reader.contents == get_input_text()
    assert test_reader.lines == get_input_lines()
    assert test_reader.n_lines == 16
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
    input_lines = get_input_lines()
    test_reader = get_test_reader()
    assert list(test_reader.pop_until("^header section")) == input_lines[:6]


def test_reader_pop_until_empty() -> None:
    input_lines = get_input_lines()
    test_reader = get_test_reader()
    assert list(test_reader.pop_until_empty()) == input_lines[:5]
