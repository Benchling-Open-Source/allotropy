from io import BytesIO

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.parsers.utils.encoding import bom_encoding, decode


def test_decode_utf_8_detected_as_windows_1254() -> None:
    test_bytes = "HeLa (😢)".encode("utf-8")  # noqa: UP012
    assert decode(BytesIO(test_bytes), encoding=CHARDET_ENCODING) == "HeLa (😢)"


def test_decode_actually_windows_1252() -> None:
    test_bytes = b"Special byte \x96"
    assert (
        decode(BytesIO(test_bytes), encoding=CHARDET_ENCODING)
        == "Special byte –"  # noqa: RUF001
    )


@pytest.mark.parametrize("codec", ["utf-16", "utf-16-le", "utf-16-be"])
def test_decode_utf_16_with_bom_without_encoding(codec: str) -> None:
    text = "Well\tAbsorbance (\u00b5L)\nA1\t0.42"
    test_bytes = ("\ufeff" + text).encode(codec)
    if codec == "utf-16":
        assert test_bytes[:2] in (b"\xff\xfe", b"\xfe\xff")
    assert decode(BytesIO(test_bytes), encoding=None) == text


def test_decode_utf_8_without_encoding_unchanged() -> None:
    test_bytes = "Well\tA1 (\u00b5L)".encode()
    assert decode(BytesIO(test_bytes), encoding=None) == "Well\tA1 (\u00b5L)"


def test_bom_encoding_leaves_stream_position() -> None:
    stream = BytesIO(b"header\nWell,A1\n")
    stream.readline()
    assert bom_encoding(stream) is None
    assert stream.tell() == len(b"header\n")
    utf16 = BytesIO("Well,A1".encode("utf-16"))
    assert bom_encoding(utf16) == "UTF-16"
    assert utf16.tell() == 0
